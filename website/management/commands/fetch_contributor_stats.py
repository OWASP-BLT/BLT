from datetime import datetime

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from website.models import Contribution, Project


class Command(BaseCommand):
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
        owner, repo = repo.split("/")

        # Authentication headers
        headers = {"Authorization": f"token {settings.GITHUB_TOKEN}"}

        # Fetch and process data
        self.fetch_and_update_data("pulls", headers, owner, repo)
        self.fetch_and_update_data("issuesopen", headers, owner, repo)
        self.fetch_and_update_data("issuesclosed", headers, owner, repo)
        self.fetch_and_update_data("commits", headers, owner, repo)
        self.fetch_and_update_data("comments", headers, owner, repo)

        self.stdout.write(self.style.SUCCESS("Successfully updated contributor stats"))

    def fetch_and_update_data(self, data_type, headers, owner, repo):
        # Define URL based on data_type
        if data_type == "pulls":
            url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
        elif data_type == "issuesopen":
            url = f"https://api.github.com/repos/{owner}/{repo}/issues?state=open"
        elif data_type == "issuesclosed":
            url = f"https://api.github.com/repos/{owner}/{repo}/issues?state=closed"
        elif data_type == "commits":
            url = f"https://api.github.com/repos/{owner}/{repo}/commits"
        elif data_type == "comments":
            url = f"https://api.github.com/repos/{owner}/{repo}/issues/comments?per_page=100"

        response = requests.get(url, headers=headers)
        items = response.json()

        if not isinstance(items, list):
            raise ValueError(f"Error fetching data from GitHub: {items['message']}")

        # Get project object
        project = Project.objects.get(github_url__contains=f"{owner}/{repo}")

        for item in items:
            if data_type == "pulls":
                user = item["user"]["login"]
                Contribution.objects.create(
                    github_username=user,
                    title=item["title"],
                    description=item["body"] or "",
                    contribution_type="pull_request",
                    github_id=str(item["id"]),
                    github_url=item["html_url"],
                    created=datetime.strptime(item["created_at"], "%Y-%m-%dT%H:%M:%SZ"),
                    status=item["state"],
                    repository=project,
                )
            elif data_type == "issuesopen":
                if "pull_request" in item:
                    continue
                user = item["user"]["login"]
                if item["state"] == "open":
                    Contribution.objects.create(
                        github_username=user,
                        title=item["title"],
                        description=item["body"] or "",
                        contribution_type="issue_opened",
                        github_id=str(item["id"]),
                        github_url=item["html_url"],
                        created=datetime.strptime(item["created_at"], "%Y-%m-%dT%H:%M:%SZ"),
                        status="open",
                        repository=project,
                    )
            elif data_type == "issuesclosed":
                if "pull_request" in item:
                    continue
                user = item["user"]["login"]
                if item["state"] == "closed":
                    Contribution.objects.create(
                        github_username=user,
                        title=item["title"],
                        description=item["body"] or "",
                        contribution_type="issue_closed",
                        github_id=str(item["id"]),
                        github_url=item["html_url"],
                        created=datetime.strptime(
                            item["closed_at"] or item["created_at"], "%Y-%m-%dT%H:%M:%SZ"
                        ),
                        status="closed",
                        repository=project,
                    )
            elif data_type == "commits":
                user = item["author"]["login"]
                Contribution.objects.create(
                    title=item["commit"]["message"],
                    description=item["commit"]["message"],
                    github_username=user,
                    contribution_type="commit",
                    github_id=user,
                    github_url=item["html_url"],
                    created=datetime.strptime(
                        item["commit"]["author"]["date"], "%Y-%m-%dT%H:%M:%SZ"
                    ),
                    repository=project,
                )
            elif data_type == "comments":
                user = item["user"]["login"]
                Contribution.objects.create(
                    title=item["body"],
                    description=item["body"],
                    github_username=user,
                    contribution_type="comment",
                    github_id=user,
                    github_url=item["html_url"],
                    created=datetime.strptime(item["created_at"], "%Y-%m-%dT%H:%M:%SZ"),
                    repository=project,
                )
