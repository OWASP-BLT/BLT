import time
from urllib.parse import urlparse

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

        repo = None

        if not hasattr(project, "url"):
            self.stdout.write(self.style.ERROR(f"Project {project.name} does not have a URL attribute"))
            return

        if not project.url:
            self.stdout.write(self.style.ERROR(f"Project {project.name} has an empty URL"))
            return

        try:
            parsed_url = urlparse(project.url.strip())

            if parsed_url.netloc == "github.com":
                repo_path = parsed_url.path.strip("/")
                if repo_path and repo_path.count("/") == 1:
                    repo = repo_path
                else:
                    self.stdout.write(
                        self.style.ERROR(f"Invalid GitHub repository format: {parsed_url.path}. Expected 'owner/repo'")
                    )
                    return
            else:
                self.stdout.write(self.style.ERROR(f"Project URL is not a GitHub repository URL: {project.url}"))
                return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error parsing URL {project.url}: {str(e)}"))
            return

        if not repo:
            self.stdout.write(self.style.ERROR("Could not extract valid GitHub repository information"))
            return

        headers = {
            "Authorization": f"token {settings.GITHUB_TOKEN}",
            "Content-Type": "application/json",
        }

        contributors = []

        # Fetch contributors
        page = 1
        while True:
            url = f"https://api.github.com/repos/{repo}/contributors?per_page=100&page={page}"
            self.stdout.write(self.style.SUCCESS(f"Fetching from: {url}"))

            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                self.stdout.write(
                    self.style.WARNING(f"Failed to fetch contributors for {repo} page {page}: {response.status_code}")
                )
                if response.status_code == 404:
                    self.stdout.write(self.style.ERROR(f"Repository '{repo}' not found. Please check the project URL."))
                elif response.status_code == 403:
                    self.stdout.write(self.style.ERROR("API rate limit exceeded or authentication issue."))
                break

            contributors_data = response.json()
            if not contributors_data:
                break

            for c in contributors_data:
                try:
                    name = str(c["login"])[:255]
                    github_url = str(c["html_url"])[:255]
                    avatar_url = str(c["avatar_url"])[:255]

                    contributor, created = Contributor.objects.get_or_create(
                        github_id=c["id"],
                        defaults={
                            "name": name,
                            "github_url": github_url,
                            "avatar_url": avatar_url,
                            "contributor_type": str(c["type"])[:255],
                            "contributions": c["contributions"],
                        },
                    )

                    if not created:
                        contributor.contributions = c["contributions"]
                        contributor.save()

                    contributors.append(contributor)

                    if created:
                        self.stdout.write(f"Created new contributor: {name}")
                    else:
                        self.stdout.write(f"Updated existing contributor: {name}")

                except MultipleObjectsReturned:
                    self.stdout.write(self.style.WARNING(f"Multiple records found for {c['login']}"))
                    contributor = Contributor.objects.filter(github_id=c["id"]).first()
                    contributors.append(contributor)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error processing contributor {c['login']}: {str(e)}"))

            if "next" not in response.links:
                break

            page += 1
            time.sleep(1)

        # Link contributors to project
        if hasattr(project, "contributors"):
            project.contributors.set(contributors)
            self.stdout.write(f"Set {len(contributors)} contributors for project {project.name}")

        if hasattr(project, "contributor_count"):
            project.contributor_count = len(contributors)
            project.save()
            self.stdout.write(f"Updated contributor count to {len(contributors)}")

        self.stdout.write(self.style.SUCCESS(f"Successfully fetched contributors for project {project.name}"))
