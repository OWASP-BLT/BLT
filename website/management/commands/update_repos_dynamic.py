import logging
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from website.management.base import LoggedBaseCommand
from website.models import GitHubIssue, Repo

logger = logging.getLogger(__name__)


class Command(LoggedBaseCommand):
    help = (
        "Dynamically updates repository data based on activity levels "
        "and fetches GitHub issues with $ in tags and closed PRs"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force-all",
            action="store_true",
            help="Force update all repositories regardless of their update schedule",
        )
        parser.add_argument(
            "--repo-id",
            type=int,
            help="Update a specific repository by ID",
        )
        parser.add_argument(
            "--skip-issues",
            action="store_true",
            help="Skip fetching issues and pull requests",
        )

    def _github_headers(self):
        headers = {"Accept": "application/vnd.github.v3+json"}
        token = getattr(settings, "GITHUB_TOKEN", None)
        if token and token.strip().lower() != "blank":
            headers["Authorization"] = f"token {token}"
        return headers

    def handle(self, *args, **options):
        force_all = options.get("force_all", False)
        repo_id = options.get("repo_id")
        skip_issues = options.get("skip_issues", False)
        now = timezone.now()

        # If a specific repo ID is provided, only update that repo
        if repo_id:
            try:
                repo = Repo.objects.get(id=repo_id)
                self.stdout.write(f"Updating specific repository: {repo.name}")
                self.update_repository(repo, skip_issues)
                self.stdout.write(self.style.SUCCESS(f"Repository update completed for {repo.name}"))
                return
            except Repo.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Repository with ID {repo_id} not found"))
                return
            except Exception as e:
                logger.error(f"Error updating repository ID {repo_id}: {e}")
                self.stdout.write(self.style.ERROR(f"Failed to update repository ID {repo_id}: {e}"))
                return

        # Otherwise, get all repositories
        repos = Repo.objects.all()
        total_repos = repos.count()

        updated_count = 0
        skipped_count = 0

        self.stdout.write(f"Found {total_repos} repositories to check for updates")

        for repo in repos:
            if self.should_update_repo(repo, now) or force_all:
                try:
                    self.update_repository(repo, skip_issues)
                    updated_count += 1
                except Exception as e:
                    logger.error(f"Error updating repository {repo.name}: {e}")
                    self.stdout.write(self.style.ERROR(f"Failed to update {repo.name}: {e}"))
            else:
                skipped_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"Repository update completed. Updated: {updated_count}, Skipped: {skipped_count}")
        )

    def should_update_repo(self, repo, current_time):
        if not repo.last_updated:
            return True
        time_since_update = current_time - repo.last_updated
        update_interval = self.calculate_update_interval(repo)
        return time_since_update >= update_interval

    def calculate_update_interval(self, repo):
        latest_activity_date = self.get_latest_issue_activity(repo)
        if not latest_activity_date:
            if repo.last_commit_date:
                latest_activity_date = repo.last_commit_date
            else:
                return timedelta(days=1)

        time_since_activity = timezone.now() - latest_activity_date

        if time_since_activity < timedelta(hours=24):
            return timedelta(hours=1)
        elif time_since_activity < timedelta(days=7):
            return timedelta(hours=3)
        elif time_since_activity < timedelta(days=30):
            return timedelta(days=1)
        elif time_since_activity < timedelta(days=90):
            return timedelta(days=3)
        else:
            return timedelta(days=7)

    def get_latest_issue_activity(self, repo):
        latest_issues = GitHubIssue.objects.filter(repo=repo).order_by("-updated_at")
        if latest_issues.exists():
            return latest_issues.first().updated_at
        if repo.open_issues > 0 or repo.open_pull_requests > 0:
            return timezone.now() - timedelta(days=1)
        return None

    def update_repository(self, repo, skip_issues=False):
        self.stdout.write(f"Updating repository: {repo.name}")

        parsed = urlparse(repo.repo_url)
        hostname = parsed.hostname.lower() if parsed.hostname else ""

        if hostname in ["github.com", "www.github.com"]:
            path = parsed.path.strip("/")
            parts = [p for p in path.split("/") if p]

            if len(parts) >= 2:
                owner, repo_name = parts[0], parts[1]
                if repo_name.endswith(".git"):
                    repo_name = repo_name[:-4]

                # Update Metadata
                success = self.update_repo_data(repo, owner, repo_name)
                if not success:
                    raise RuntimeError(f"Failed to fetch metadata for {repo.name}")

                # Update Issues (Optional)
                if not skip_issues:
                    self.fetch_issues_and_prs(repo, owner, repo_name)
            else:
                raise RuntimeError(f"Invalid GitHub URL format for {repo.name}")
        else:
            raise RuntimeError(f"Not a GitHub URL for {repo.name}")

        repo.last_updated = timezone.now()
        repo.save(update_fields=["last_updated"])
        self.stdout.write(self.style.SUCCESS(f"Successfully updated {repo.name}"))

    def update_repo_data(self, repo, owner, repo_name):
        headers = self._github_headers()

        try:
            url = f"https://api.github.com/repos/{owner}/{repo_name}"
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            repo_data = response.json()

            repo.stars = repo_data.get("stargazers_count", 0)
            repo.forks = repo_data.get("forks_count", 0)
            repo.open_issues = repo_data.get("open_issues_count", 0)
            repo.watchers = repo_data.get("watchers_count", 0)

            description = repo_data.get("description") or ""
            if len(description) > 255:
                description = description[:252] + "..."
            repo.description = description

            repo.primary_language = repo_data.get("language") or ""
            repo.is_archived = repo_data.get("archived", False)

            if "pushed_at" in repo_data:
                repo.last_commit_date = timezone.make_aware(
                    datetime.strptime(repo_data["pushed_at"], "%Y-%m-%dT%H:%M:%SZ"), dt_timezone.utc
                )

            repo.save(
                update_fields=[
                    "stars",
                    "forks",
                    "open_issues",
                    "watchers",
                    "description",
                    "primary_language",
                    "is_archived",
                    "last_commit_date",
                ]
            )
            return True

        # HERE IS S3DFX-CYBER'S FIX COMBINED PERFECTLY
        except (requests.exceptions.RequestException, ValueError) as e:
            logger.error(f"Error fetching repository data for {owner}/{repo_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error fetching repository data for {owner}/{repo_name}: {e}")
            return False

    def fetch_issues_and_prs(self, repo, owner, repo_name):
        dollar_issues = self.fetch_dollar_issues(owner, repo_name)
        closed_prs = self.fetch_closed_prs(owner, repo_name)
        self.save_issues_and_prs(repo, dollar_issues, closed_prs)

        msg = f"Found {len(dollar_issues)} issues with $ tags and {len(closed_prs)} closed PRs"
        self.stdout.write(self.style.SUCCESS(msg))

    def fetch_dollar_issues(self, owner, repo_name):
        issues = []
        page = 1
        per_page = 100
        headers = self._github_headers()

        while True:
            url = (
                f"https://api.github.com/repos/{owner}/{repo_name}/issues"
                f"?state=open&per_page={per_page}&page={page}"
            )

            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                if not data:
                    break

                for issue in data:
                    if "pull_request" in issue:
                        continue

                    labels = issue.get("labels", [])
                    has_dollar = any("$" in label.get("name", "") for label in labels)
                    if has_dollar:
                        issues.append(issue)

                page += 1
                if len(data) < per_page:
                    break

            except (requests.exceptions.RequestException, ValueError) as e:
                logger.error(f"Error fetching issues for {owner}/{repo_name}: {e}")
                break

        return issues

    def fetch_closed_prs(self, owner, repo_name):
        prs = []
        page = 1
        per_page = 100
        headers = self._github_headers()

        while True:
            url = (
                f"https://api.github.com/repos/{owner}/{repo_name}/pulls"
                f"?state=closed&per_page={per_page}&page={page}&sort=updated&direction=desc"
            )

            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()
                if not data:
                    break
                filtered_data = []
                for pr in data:
                    updated_at = datetime.strptime(pr["updated_at"], "%Y-%m-%dT%H:%M:%SZ")
                    updated_at = timezone.make_aware(updated_at, timezone=dt_timezone.utc)

                    if updated_at >= timezone.now() - timedelta(days=365):
                        filtered_data.append(pr)
                    else:
                        break

                if not filtered_data:
                    break

                prs.extend(filtered_data)
                page += 1
                if len(data) < per_page:
                    break

            except (requests.exceptions.RequestException, ValueError) as e:
                logger.error(f"Error fetching closed PRs for {owner}/{repo_name}: {e}")
                break

        return prs

    def save_issues_and_prs(self, repo, dollar_issues, closed_prs):
        for issue in dollar_issues:
            try:
                with transaction.atomic():
                    GitHubIssue.objects.update_or_create(
                        issue_id=issue["number"],
                        repo=repo,
                        defaults={
                            "title": issue["title"],
                            "body": issue.get("body") or "",
                            "state": issue["state"],
                            "type": "issue",
                            "created_at": timezone.make_aware(
                                datetime.strptime(issue["created_at"], "%Y-%m-%dT%H:%M:%SZ"), dt_timezone.utc
                            ),
                            "updated_at": timezone.make_aware(
                                datetime.strptime(issue["updated_at"], "%Y-%m-%dT%H:%M:%SZ"), dt_timezone.utc
                            ),
                            "closed_at": timezone.make_aware(
                                datetime.strptime(issue["closed_at"], "%Y-%m-%dT%H:%M:%SZ"), dt_timezone.utc
                            )
                            if issue.get("closed_at")
                            else None,
                            "url": issue["html_url"],
                            "has_dollar_tag": True,
                        },
                    )
            except Exception as e:
                logger.error(f"Error saving issue #{issue['number']}: {e}")

        for pr in closed_prs:
            try:
                with transaction.atomic():
                    GitHubIssue.objects.update_or_create(
                        issue_id=pr["number"],
                        repo=repo,
                        defaults={
                            "title": pr["title"],
                            "body": pr.get("body") or "",
                            "state": pr["state"],
                            "type": "pull_request",
                            "created_at": timezone.make_aware(
                                datetime.strptime(pr["created_at"], "%Y-%m-%dT%H:%M:%SZ"), dt_timezone.utc
                            ),
                            "updated_at": timezone.make_aware(
                                datetime.strptime(pr["updated_at"], "%Y-%m-%dT%H:%M:%SZ"), dt_timezone.utc
                            ),
                            "closed_at": timezone.make_aware(
                                datetime.strptime(pr["closed_at"], "%Y-%m-%dT%H:%M:%SZ"), dt_timezone.utc
                            )
                            if pr.get("closed_at")
                            else None,
                            "merged_at": timezone.make_aware(
                                datetime.strptime(pr["merged_at"], "%Y-%m-%dT%H:%M:%SZ"), dt_timezone.utc
                            )
                            if pr.get("merged_at")
                            else None,
                            "is_merged": bool(pr.get("merged_at")),
                            "url": pr["html_url"],
                        },
                    )
            except Exception as e:
                logger.error(f"Error saving PR #{pr['number']}: {e}")
