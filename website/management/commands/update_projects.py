from urllib.parse import quote_plus

import requests
from django.conf import settings
from django.utils.dateparse import parse_datetime

from website.management.base import LoggedBaseCommand
from website.models import Project


class Command(LoggedBaseCommand):
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
            projects = Project.objects.filter(id=project_id).prefetch_related("contributor")
        else:
            projects = Project.objects.prefetch_related("contributor").all()

        headers = {
            "Authorization": f"token {settings.GITHUB_TOKEN}",
            "Content-Type": "application/json",
        }

        for project in projects:
            owner_repo = project.github_url.rstrip("/").split("/")[-2:]
            repo_name = f"{owner_repo[0]}/{owner_repo[1]}"
            contributors = []

            # Fetch repository data
            url = f"https://api.github.com/repos/{repo_name}"
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
                project.last_commit_date = parse_datetime(repo_data.get("pushed_at"))

                # Fetch counts of issues and pull requests using the Search API
                def get_issue_count(repo_name, query, headers):
                    encoded_query = quote_plus(f"repo:{repo_name} {query}")
                    url = f"https://api.github.com/search/issues?q={encoded_query}"
                    response = requests.get(url, headers=headers)
                    if response.status_code == 200:
                        data = response.json()
                        return data.get("total_count", 0)
                    else:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Failed to fetch issue count for {repo_name} with query '{query}': {response.status_code}"
                            )
                        )
                        return 0

                project.open_issues = get_issue_count(repo_name, "type:issue state:open", headers)
                project.closed_issues = get_issue_count(repo_name, "type:issue state:closed", headers)
                project.open_pull_requests = get_issue_count(repo_name, "type:pr state:open", headers)
                project.closed_pull_requests = get_issue_count(repo_name, "type:pr state:closed", headers)

                # Fetch latest release
                url = f"https://api.github.com/repos/{repo_name}/releases/latest"
                response = requests.get(url, headers=headers)
                if response.status_code == 200:
                    release_data = response.json()
                    project.release_name = release_data.get("name") or release_data.get("tag_name")
                    project.release_datetime = parse_datetime(release_data.get("published_at"))
                else:
                    self.stdout.write(self.style.WARNING(f"No releases found for {repo_name}: {response.status_code}"))

                page = 1
                commit_count = 0
                while True:
                    url = f"https://api.github.com/repos/{repo_name}/contributors?anon=true&per_page=100&page={page}"
                    response = requests.get(url, headers=headers)
                    if response.status_code == 200:
                        contributors_data = response.json()
                        if not contributors_data:
                            break
                        commit_count += sum(contributor.get("contributions", 0) for contributor in contributors_data)
                        page += 1
                    else:
                        self.stdout.write(
                            self.style.WARNING(f"Failed to fetch contributors for {repo_name}: {response.status_code}")
                        )
                        break
                project.commit_count = commit_count
                project.save()

            else:
                self.stdout.write(
                    self.style.WARNING(f"Failed to fetch repository data for {repo_name}: {response.status_code}")
                )
                continue  # Skip to next project

        self.stdout.write(self.style.SUCCESS(f"Successfully updated {len(projects)} projects"))

        # Additional stats that can be pulled from GitHub APIs:
        # - Traffic statistics (clones, views) via the Traffic API (requires push access)
        # - Code frequency (additions/deletions) via the Stats API
        # - Participation (commits per week) via the Stats API
        # - Language breakdown via the Languages API
        # - Tags and branches via the Tags and Branches API
        # - Repository topics via the Topics API
        # - Dependency graph via the Dependency Graph API (requires certain permissions)
        # - GitHub Actions workflows and runs via the Actions API
        # - Security vulnerability alerts via the Security Advisories API
        # - Repository invitations via the Collaborators API
        # - Check if the repository is archived, disabled, or a fork via the Repository object
