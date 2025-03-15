import requests
from django.conf import settings

from website.management.base import LoggedBaseCommand
from website.models import Repo
from website.utils import ai_summary, markdown_to_text


class Command(LoggedBaseCommand):
    help = "Fetches readme content of the repositories and generates and stores an AI summary."

    def handle(self, *args, **options):
        github_token = getattr(settings, "GITHUB_TOKEN", None)

        self.stderr.write(self.style.WARNING("RUNNING"))

        if not github_token:
            self.stderr.write(self.style.ERROR("GITHUB_TOKEN is not configured in settings. Aborting."))
            return

        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        repos = Repo.objects.all()

        for repo in repos:
            repo_url_suffix = repo.repo_url.split("github.com/")[-1]
            raw_readme_urls = [
                f"https://raw.githubusercontent.com/{repo_url_suffix}/main/README.md",
                f"https://raw.githubusercontent.com/{repo_url_suffix}/master/README.md",
            ]

            readme_fetched = False

            for url in raw_readme_urls:
                try:
                    response = requests.get(url, headers=headers)
                    if response.status_code == 200:
                        repo.readme_content = response.text
                        repo.save()
                        self.stderr.write(self.style.SUCCESS(f"Readme content fetched for {repo.name}"))
                        readme_fetched = True
                        break
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"Error fetching README for {repo.name}: {e}"))

            if not readme_fetched:
                self.stderr.write(self.style.ERROR(f"Could not fetch README for {repo.name} at {repo.repo_url}"))
                continue

            try:
                summary = ai_summary(markdown_to_text(repo.readme_content))
                repo.ai_summary = summary
                repo.save()
                self.stderr.write(self.style.SUCCESS(f"Summary generated for {repo.name}"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error generating summary for {repo.name}: {e}"))
                continue

