import time

import requests
from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned

from website.management.base import LoggedBaseCommand
from website.models import Contributor, Project


class Command(LoggedBaseCommand):
    help = "Fetch contributors for a specified project from GitHub"

    def add_arguments(self, parser):
        parser.add_argument(
            "--project_id",
            type=int,
            help="Specify a project ID to fetch contributors for that project",
        )

    def handle(self, *args, **kwargs):
        project_id = kwargs.get("project_id")
        if not project_id:
            self.stdout.write(self.style.ERROR("Please provide a project ID using --project_id"))
            return

        try:
            project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Project with ID {project_id} does not exist"))
            return

        headers = {
            "Authorization": f"token {settings.GITHUB_TOKEN}",
            "Content-Type": "application/json",
        }

        owner_repo = project.github_url.rstrip("/").split("/")[-2:]
        repo_name = f"{owner_repo[0]}/{owner_repo[1]}"
        contributors = []

        # Fetch contributors
        page = 1
        while True:
            url = f"https://api.github.com/repos/{repo_name}/contributors?per_page=100&page={page}"
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                self.stdout.write(
                    self.style.WARNING(
                        f"Failed to fetch contributors for {repo_name} page {page}: {response.status_code}"
                    )
                )
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

            if "next" not in response.links:
                break

            page += 1
            # Respect GitHub's rate limits
            time.sleep(1)

        project.contributors.set(contributors)
        project.contributor_count = len(contributors)
        project.save()

        self.stdout.write(self.style.SUCCESS(f"Successfully fetched contributors for project {project.name}"))
