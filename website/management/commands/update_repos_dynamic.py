import logging
from datetime import datetime, timedelta

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
        """
        Determine if a repository should be updated based on its activity level.

        Returns True if the repository should be updated, False otherwise.
        """
        # If the repository has never been updated, update it now
        if not repo.last_updated:
            return True

        # Calculate time since last update
        time_since_update = current_time - repo.last_updated

        # Determine update interval based on activity level
        update_interval = self.calculate_update_interval(repo)

        # Check if enough time has passed since the last update
        return time_since_update >= update_interval

    def calculate_update_interval(self, repo):
        """
        Calculate the appropriate update interval based on repository activity.

        Returns a timedelta representing how often the repository should be updated.
        """
        # Get the most recent issue or PR activity date
        latest_activity_date = self.get_latest_issue_activity(repo)

        # If we have no activity data, use the repo's last_commit_date or default to a moderate frequency
        if not latest_activity_date:
            if repo.last_commit_date:
                latest_activity_date = repo.last_commit_date
            else:
                # No activity data available, use a default interval
                return timedelta(days=1)

        # Calculate how long ago the latest activity was
        time_since_activity = timezone.now() - latest_activity_date

        # Determine update frequency based on recent activity
        if time_since_activity < timedelta(hours=24):
            # Very recent activity (last 24 hours) - update frequently
            return timedelta(hours=1)
        elif time_since_activity < timedelta(days=7):
            # Recent activity (last week) - update every few hours
            return timedelta(hours=3)
        elif time_since_activity < timedelta(days=30):
            # Activity within the last month - update daily
            return timedelta(days=1)
        elif time_since_activity < timedelta(days=90):
            # Activity within the last quarter - update every few days
            return timedelta(days=3)
        else:
            # Dormant repository - update weekly
            return timedelta(days=7)

    def get_latest_issue_activity(self, repo):
        """
        Get the date of the most recent issue or PR activity for a repository.

        Returns the most recent date or None if no activity is found.
        """
        # Check if the repo has any GitHub issues in our database
        latest_issues = GitHubIssue.objects.filter(repo=repo).order_by("-updated_at")

        if latest_issues.exists():
            return latest_issues.first().updated_at

        # If we don't have any issues in our database, check if the repo has open issues
        if repo.open_issues > 0 or repo.open_pull_requests > 0:
            # There are open issues or PRs, but we don't have them in our database
            # This suggests recent activity, so we'll return a recent date
            return timezone.now() - timedelta(days=1)

        # No issue activity found
        return None

    @transaction.atomic
    def update_repository(self, repo, skip_issues=False):
        """
        Update the repository data from GitHub.
        """
        self.stdout.write(f"Updating repository: {repo.name}")

        # Extract owner and repo name from the repo URL
        repo_url_parts = repo.repo_url.split("/")
        if "github.com" in repo.repo_url and len(repo_url_parts) >= 5:
            owner = repo_url_parts[-2]
            repo_name = repo_url_parts[-1]

            # Update repository data from GitHub API
            self.update_repo_data(repo, owner, repo_name)

            # Fetch issues with $ in tags and closed PRs if not skipped
            if not skip_issues:
                self.fetch_issues_and_prs(repo, owner, repo_name)
        else:
            self.stdout.write(self.style.WARNING(f"Not a valid GitHub repository URL: {repo.repo_url}"))

        # Update the last_updated timestamp
        repo.last_updated = timezone.now()
        repo.save(update_fields=["last_updated"])

        self.stdout.write(self.style.SUCCESS(f"Successfully updated {repo.name}"))

    def update_repo_data(self, repo, owner, repo_name):
        """
        Update repository data from GitHub API.
        """
        headers = {"Accept": "application/vnd.github.v3+json"}
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

        try:
            # Get repository data
            url = f"https://api.github.com/repos/{owner}/{repo_name}"
            response = requests.get(url, headers=headers)
            response.raise_for_status()

            repo_data = response.json()

            # Update repository fields
            repo.stars = repo_data.get("stargazers_count", 0)
            repo.forks = repo_data.get("forks_count", 0)
            repo.open_issues = repo_data.get("open_issues_count", 0)
            repo.watchers = repo_data.get("watchers_count", 0)

            # Truncate description if it's too long to prevent database errors
            description = repo_data.get("description", "")
            if description and len(description) > 255:
                description = description[:252] + "..."
            repo.description = description

            repo.primary_language = repo_data.get("language", "")
            repo.is_archived = repo_data.get("archived", False)

            # Update last commit date if available
            if "pushed_at" in repo_data:
                repo.last_commit_date = timezone.make_aware(
                    datetime.strptime(repo_data["pushed_at"], "%Y-%m-%dT%H:%M:%SZ")
                )

            # Save the updated repository data
            repo.save()

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching repository data for {owner}/{repo_name}: {e}")

    def fetch_issues_and_prs(self, repo, owner, repo_name):
        """
        Fetch GitHub issues with $ in tags and closed pull requests.
        """
        # Fetch issues with $ in labels
        dollar_issues = self.fetch_dollar_issues(owner, repo_name)

        # Fetch closed pull requests
        closed_prs = self.fetch_closed_prs(owner, repo_name)

        # Save the results to the database
        self.save_issues_and_prs(repo, dollar_issues, closed_prs)

        # Log the results
        msg = f"Found {len(dollar_issues)} issues with $ tags and " f"{len(closed_prs)} closed PRs for {repo.name}"
        self.stdout.write(self.style.SUCCESS(msg))

    def fetch_dollar_issues(self, owner, repo_name):
        """
        Fetch issues with $ in labels from GitHub API.
        """
        issues = []
        page = 1
        per_page = 100

        headers = {"Accept": "application/vnd.github.v3+json"}
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

        while True:
            # GitHub API doesn't support direct search for $ in labels, so we'll fetch all issues and filter
            url = (
                f"https://api.github.com/repos/{owner}/{repo_name}/issues"
                f"?state=open&per_page={per_page}&page={page}"
            )

            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()

                data = response.json()
                if not data:
                    break

                # Filter issues with $ in labels
                for issue in data:
                    # Skip pull requests (they have a 'pull_request' key)
                    if "pull_request" in issue:
                        continue

                    # Check if any label contains $
                    has_dollar_label = False
                    for label in issue.get("labels", []):
                        if "$" in label.get("name", ""):
                            has_dollar_label = True
                            break

                    if has_dollar_label:
                        issues.append(issue)

                page += 1

                # Check if we've reached the last page
                if len(data) < per_page:
                    break

            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching issues for {owner}/{repo_name}: {e}")
                break

        return issues

    def fetch_closed_prs(self, owner, repo_name):
        """
        Fetch closed pull requests from GitHub API.
        Only fetches PRs from the past year.
        """
        prs = []
        page = 1
        per_page = 100

        # Calculate date one year ago for filtering
        one_year_ago = (timezone.now() - timedelta(days=365)).strftime("%Y-%m-%dT%H:%M:%SZ")

        headers = {"Accept": "application/vnd.github.v3+json"}
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

        while True:
            url = (
                f"https://api.github.com/repos/{owner}/{repo_name}/pulls"
                f"?state=closed&per_page={per_page}&page={page}&sort=updated&direction=desc"
                f"&since={one_year_ago}"
            )

            self.stdout.write(f"Fetching PRs from: {url}")

            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()

                data = response.json()
                if not data:
                    break

                # Filter PRs to only include those updated in the last year
                filtered_data = []
                for pr in data:
                    updated_at = datetime.strptime(pr["updated_at"], "%Y-%m-%dT%H:%M:%SZ")
                    updated_at = timezone.make_aware(updated_at)
                    if updated_at >= timezone.now() - timedelta(days=365):
                        filtered_data.append(pr)
                    else:
                        # Since results are sorted by updated_at, we can break early
                        break

                if not filtered_data:
                    break

                prs.extend(filtered_data)
                self.stdout.write(f"Found {len(filtered_data)} PRs on page {page}")

                page += 1

                # Check if we've reached the last page
                if len(data) < per_page:
                    break

            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching closed PRs for {owner}/{repo_name}: {e}")
                break

        self.stdout.write(f"Total PRs fetched: {len(prs)}")
        return prs

    @transaction.atomic
    def save_issues_and_prs(self, repo, dollar_issues, closed_prs):
        """
        Save the fetched issues and PRs to the database.
        """
        # Process issues with $ in labels
        for issue in dollar_issues:
            try:
                GitHubIssue.objects.update_or_create(
                    issue_id=issue["number"],
                    repo=repo,
                    defaults={
                        "title": issue["title"],
                        "body": issue.get("body", ""),
                        "state": issue["state"],
                        "type": "issue",
                        "created_at": timezone.make_aware(datetime.strptime(issue["created_at"], "%Y-%m-%dT%H:%M:%SZ")),
                        "updated_at": timezone.make_aware(datetime.strptime(issue["updated_at"], "%Y-%m-%dT%H:%M:%SZ")),
                        "closed_at": timezone.make_aware(datetime.strptime(issue["closed_at"], "%Y-%m-%dT%H:%M:%SZ"))
                        if issue.get("closed_at")
                        else None,
                        "url": issue["html_url"],
                        "has_dollar_tag": True,
                    },
                )
            except Exception as e:
                logger.error(f"Error saving issue #{issue['number']} for repo {repo.name}: {e}")
                self.stdout.write(self.style.ERROR(f"Failed to save issue #{issue['number']}: {e}"))

        # Process closed pull requests
        for pr in closed_prs:
            try:
                GitHubIssue.objects.update_or_create(
                    issue_id=pr["number"],
                    repo=repo,
                    defaults={
                        "title": pr["title"],
                        "body": pr.get("body", ""),
                        "state": pr["state"],
                        "type": "pull_request",
                        "created_at": timezone.make_aware(datetime.strptime(pr["created_at"], "%Y-%m-%dT%H:%M:%SZ")),
                        "updated_at": timezone.make_aware(datetime.strptime(pr["updated_at"], "%Y-%m-%dT%H:%M:%SZ")),
                        "closed_at": timezone.make_aware(datetime.strptime(pr["closed_at"], "%Y-%m-%dT%H:%M:%SZ"))
                        if pr.get("closed_at")
                        else None,
                        "merged_at": timezone.make_aware(datetime.strptime(pr["merged_at"], "%Y-%m-%dT%H:%M:%SZ"))
                        if pr.get("merged_at")
                        else None,
                        "is_merged": bool(pr.get("merged_at")),
                        "url": pr["html_url"],
                    },
                )
            except Exception as e:
                logger.error(f"Error saving PR #{pr['number']} for repo {repo.name}: {e}")
                self.stdout.write(self.style.ERROR(f"Failed to save PR #{pr['number']}: {e}"))

