import requests
from django.core.exceptions import MultipleObjectsReturned
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
            response = requests.get(url, headers={"Content-Type": "application/json"})
            if response.status_code == 200:
                repo_data = response.json()
                project.stars = repo_data.get("stargazers_count", 0)
                project.forks = repo_data.get("forks_count", 0)
                project.total_issues = repo_data.get(
                    "open_issues_count", 0
                )  # Directly use open_issues_count

                # Fetch last commit date
                commits_url = f"https://api.github.com/repos/{repo_name}/commits"
                commits_response = requests.get(
                    commits_url, headers={"Content-Type": "application/json"}
                )
                if commits_response.status_code == 200:
                    commits_data = commits_response.json()
                    if commits_data:
                        last_commit_date = (
                            commits_data[0].get("commit", {}).get("committer", {}).get("date")
                        )
                        project.last_updated = parse_datetime(last_commit_date)

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
