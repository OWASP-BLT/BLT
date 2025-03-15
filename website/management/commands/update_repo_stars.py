import logging
import time

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from website.models import ManagementCommandLog, Repo

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Update repository star counts from GitHub API"

    def handle(self, *args, **options):
        command_name = "update_repo_stars"
        log_entry, created = ManagementCommandLog.objects.get_or_create(command_name=command_name)
        log_entry.run_count += 1
        log_entry.save()

        try:
            self.stdout.write(self.style.SUCCESS("Starting repository star count update..."))

            # Get all repositories
            repos = Repo.objects.all()
            self.stdout.write(f"Found {repos.count()} repositories to update")

            updated_count = 0
            error_count = 0

            for repo in repos:
                try:
                    # Extract owner and repo name from repo_url
                    if "github.com" in repo.repo_url:
                        parts = repo.repo_url.split("github.com/")
                        if len(parts) > 1:
                            repo_path = parts[1].strip("/")

                            # Make API request to GitHub
                            api_url = f"https://api.github.com/repos/{repo_path}"
                            headers = {"Accept": "application/vnd.github.v3+json"}

                            # Add GitHub token if available
                            github_token = None
                            if github_token:
                                headers["Authorization"] = f"token {github_token}"

                            response = requests.get(api_url, headers=headers)

                            if response.status_code == 200:
                                data = response.json()

                                # Update repository information
                                repo.stars = data.get("stargazers_count", 0)
                                repo.forks = data.get("forks_count", 0)
                                repo.watchers = data.get("watchers_count", 0)
                                repo.open_issues = data.get("open_issues_count", 0)
                                repo.last_updated = timezone.now()

                                # Save changes
                                repo.save()
                                updated_count += 1
                                self.stdout.write(f"Updated {repo.name}: {repo.stars} stars")
                            else:
                                self.stdout.write(
                                    self.style.WARNING(f"Failed to fetch data for {repo.name}: {response.status_code}")
                                )
                                error_count += 1

                            # Sleep to avoid rate limiting
                            time.sleep(1)
                    else:
                        self.stdout.write(self.style.WARNING(f"Skipping {repo.name}: Not a GitHub repository"))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error updating {repo.name}: {str(e)}"))
                    error_count += 1

            self.stdout.write(
                self.style.SUCCESS(f"Repository update completed. Updated: {updated_count}, Errors: {error_count}")
            )

            log_entry.success = True
            log_entry.error_message = None
            log_entry.save()

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Command failed: {str(e)}"))
            log_entry.success = False
            log_entry.error_message = str(e)
            log_entry.save()

