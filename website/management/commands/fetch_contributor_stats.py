from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import requests
from django.conf import settings

from website.management.base import LoggedBaseCommand
from website.models import Contribution, Project, Repo


class Command(LoggedBaseCommand):
    help = "Fetches and updates contributor statistics from GitHub"

    def add_arguments(self, parser):
        parser.add_argument(
            "--repo",
            type=str,
            default="OWASP-BLT/BLT",
            help="Specify the GitHub repository in the format 'owner/repo'",
        )

    def handle(self, **options):
        # Clear existing records
        Contribution.objects.all().delete()

        # GitHub repository details
        repo = options["repo"]
        owner, repo_name = repo.split("/")

        # Authentication headers
        headers = {"Authorization": f"token {settings.GITHUB_TOKEN}"}

        # Find the repository
        try:
            # First try to find the repo directly
            repository = Repo.objects.get(repo_url__contains=f"{owner}/{repo_name}")
            project = repository.project
        except Repo.DoesNotExist:
            try:
                # If repo not found, try to find a project with a repo containing this path
                project = Project.objects.filter(repos__repo_url__contains=f"{owner}/{repo_name}").first()
                if not project:
                    self.stdout.write(self.style.ERROR(f"No project found with repository {owner}/{repo_name}"))
                    return
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error finding project: {str(e)}"))
                return

        # Fetch and process data in parallel
        data_types = ["pulls", "issuesopen", "issuesclosed", "commits", "comments"]
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(self.fetch_and_update_data, data_type, headers, owner, repo_name, project)
                for data_type in data_types
            ]
            for future in futures:
                future.result()  # Wait for all tasks to complete

        self.stdout.write(self.style.SUCCESS("Successfully updated contributor stats"))

    def fetch_and_update_data(self, data_type, headers, owner, repo, project):
        # Define URL based on data_type
        base_urls = {
            "pulls": f"https://api.github.com/repos/{owner}/{repo}/pulls?state=all&per_page=100",
            "issuesopen": f"https://api.github.com/repos/{owner}/{repo}/issues?state=open&per_page=100",
            "issuesclosed": f"https://api.github.com/repos/{owner}/{repo}/issues?state=closed&per_page=100",
            "commits": f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=100",
            "comments": f"https://api.github.com/repos/{owner}/{repo}/issues/comments?per_page=100",
        }
        url = base_urls[data_type]

        items = []
        while url:
            response = requests.get(url, headers=headers)
            if response.status_code != 200:
                self.stdout.write(self.style.ERROR(f"Error fetching {data_type}: {response.json()}"))
                break
            data = response.json()
            if not data:
                break
            items.extend(data)

            # Parse the 'Link' header to find the next URL
            if "Link" in response.headers:
                links = response.headers["Link"]
                next_url = None
                for link in links.split(","):
                    if 'rel="next"' in link:
                        next_url = link[link.find("<") + 1 : link.find(">")]
                        break
                url = next_url
            else:
                url = None

        contributions_to_create = []

        for item in items:
            if data_type == "pulls":
                user = item["user"]["login"]
                contributions_to_create.append(
                    Contribution(
                        github_username=user,
                        title=item["title"][:255],  # Truncate to 255 characters
                        description=(item.get("body") or "")[:255],  # Truncate to 255 characters
                        contribution_type="pull_request",
                        github_id=str(item["id"]),
                        github_url=item["html_url"],
                        created=datetime.strptime(item["created_at"], "%Y-%m-%dT%H:%M:%SZ"),
                        status=item["state"],
                        repository=project,
                    )
                )
            elif data_type == "issuesopen":
                if "pull_request" in item:
                    continue
                user = item["user"]["login"]
                contributions_to_create.append(
                    Contribution(
                        github_username=user,
                        title=item["title"],
                        description=item.get("body") or "",
                        contribution_type="issue_opened",
                        github_id=str(item["id"]),
                        github_url=item["html_url"],
                        created=datetime.strptime(item["created_at"], "%Y-%m-%dT%H:%M:%SZ"),
                        status="open",
                        repository=project,
                    )
                )
            elif data_type == "issuesclosed":
                if "pull_request" in item:
                    continue
                user = item["user"]["login"]
                contributions_to_create.append(
                    Contribution(
                        github_username=user,
                        title=item["title"],
                        description=item.get("body") or "",
                        contribution_type="issue_closed",
                        github_id=str(item["id"]),
                        github_url=item["html_url"],
                        created=datetime.strptime(item.get("closed_at") or item["created_at"], "%Y-%m-%dT%H:%M:%SZ"),
                        status="closed",
                        repository=project,
                    )
                )
            elif data_type == "commits":
                if item["author"] is None:
                    continue  # Skip commits without an associated GitHub user
                user = item["author"]["login"]
                contributions_to_create.append(
                    Contribution(
                        title=item["commit"]["message"][:255],  # Truncate to 255 characters
                        description=item["commit"]["message"][:255],  # Truncate to 255 characters
                        github_username=user,
                        contribution_type="commit",
                        github_id=item["sha"],
                        github_url=item["html_url"],
                        created=datetime.strptime(item["commit"]["author"]["date"], "%Y-%m-%dT%H:%M:%SZ"),
                        repository=project,
                    )
                )
            elif data_type == "comments":
                user = item["user"]["login"]
                contributions_to_create.append(
                    Contribution(
                        title=item["body"][:255],  # Truncate to 255 characters
                        description=item["body"][:255],  # Truncate to 255 characters
                        github_username=user,
                        contribution_type="comment",
                        github_id=str(item["id"]),
                        github_url=item["html_url"],
                        created=datetime.strptime(item["created_at"], "%Y-%m-%dT%H:%M:%SZ"),
                        repository=project,
                    )
                )

        # Bulk create contributions
        Contribution.objects.bulk_create(contributions_to_create, ignore_conflicts=True)

