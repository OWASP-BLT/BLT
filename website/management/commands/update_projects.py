import time

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils.dateparse import parse_datetime

from website.models import Contributor, Project


class Command(BaseCommand):
    help = "Update projects with their contributors and latest release from GitHub"

    def add_arguments(self, parser):
        parser.add_argument(
            "--project_id",
            type=int,
            help="Specify a project ID to update only that project",
        )

    def handle(self, *args, **kwargs):
        project_id = kwargs.get("project_id")
        if project_id:
            projects = Project.objects.filter(id=project_id).prefetch_related("contributors")
        else:
            projects = Project.objects.prefetch_related("contributors").all()

        for project in projects:
            owner_repo = project.github_url.rstrip("/").split("/")[-2:]
            repo_name = f"{owner_repo[0]}/{owner_repo[1]}"
            contributors = []

            page = 1
            while True:
                url = f"https://api.github.com/repos/{repo_name}/contributors?per_page=100&page={page}"
                print(f"Fetching contributors from URL: {url}")
                response = requests.get(url, headers={"Content-Type": "application/json"})

                if response.status_code != 200:
                    break

                contributors_data = response.json()
                if not contributors_data:
                    break

                for c in contributors_data:
                    try:
                        contributor, created = Contributor.objects.get_or_create(
                            github_id=c["id"],
                            defaults={
                                "name": c["login"],
                                "github_url": c["html_url"],
                                "avatar_url": c["avatar_url"],
                                "contributor_type": c["type"],
                                "contributions": c["contributions"],
                            },
                        )
                        contributors.append(contributor)
                    except MultipleObjectsReturned:
                        contributor = Contributor.objects.filter(github_id=c["id"]).first()
                        contributors.append(contributor)

                page += 1

            # Fetch stars, forks, and issues count
            url = f"https://api.github.com/repos/{repo_name}"
            headers = {"Authorization": f"token {settings.GITHUB_TOKEN}"}
            response = requests.get(url, headers=headers)

            if response.status_code == 200:
                repo_data = response.json()
                project.stars = repo_data.get("stargazers_count", 0)
                project.forks = repo_data.get("forks_count", 0)
                project.watchers = repo_data.get("subscribers_count", 0)
                project.network_count = repo_data.get("network_count", 0)
                project.subscribers_count = repo_data.get("subscribers_count", 0)
                project.primary_language = repo_data.get("language")
                project.license = repo_data.get("license", {}).get("name")
                project.created_at = parse_datetime(repo_data.get("created_at"))
                project.updated_at = parse_datetime(repo_data.get("updated_at"))
                project.size = repo_data.get("size", 0)

                # Get closed issues count with proper pagination
                closed_issues_count = 0
                page = 1
                while True:
                    closed_issues_url = (
                        f"https://api.github.com/repos/{repo_name}/issues"
                        f"?state=closed&per_page=100&page={page}"
                    )
                    closed_response = requests.get(closed_issues_url, headers=headers)

                    if closed_response.status_code != 200:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Failed to fetch page {page} of closed issues: {closed_response.status_code}"
                            )
                        )
                        break

                    issues = closed_response.json()
                    if not issues:
                        break

                    # Filter out pull requests
                    actual_issues = [issue for issue in issues if "pull_request" not in issue]
                    closed_issues_count += len(actual_issues)

                    # Check if we've reached the last page
                    if "next" not in closed_response.links:
                        break

                    page += 1
                    # Respect GitHub's rate limits
                    time.sleep(1)

                project.closed_issues = closed_issues_count
                project.open_issues = (
                    repo_data.get("open_issues_count", 0) - project.open_pull_requests
                )

                # Get open PRs count
                pr_url = f"https://api.github.com/repos/{repo_name}/pulls?state=open&per_page=100"
                pr_response = requests.get(pr_url, headers=headers)
                if pr_response.status_code == 200:
                    project.open_pull_requests = len(pr_response.json())

                # Get last commit
                commits_url = f"https://api.github.com/repos/{repo_name}/commits"
                commits_response = requests.get(commits_url, headers=headers)
                if commits_response.status_code == 200:
                    commits = commits_response.json()
                    if commits:
                        project.last_commit_date = parse_datetime(
                            commits[0].get("commit", {}).get("committer", {}).get("date")
                        )

            # Fetch latest release
            url = f"https://api.github.com/repos/{repo_name}/releases/latest"
            response = requests.get(url, headers={"Content-Type": "application/json"})
            if response.status_code == 200:
                release_data = response.json()
                project.release_name = release_data.get("name") or release_data.get("tag_name")
                project.release_datetime = parse_datetime(release_data.get("published_at"))

            project.contributors.set(contributors)
            project.contributor_count = len(contributors)
            project.save()

        self.stdout.write(self.style.SUCCESS(f"Successfully updated {len(projects)} projects"))
