import logging
from datetime import datetime, timedelta

import pytz
import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from website.models import GitHubIssue, Repo, UserProfile
from website.views.constants import GSOC25_PROJECTS

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch closed pull requests from the past year for GitHub repositories listed on the GSoC page"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=365,
            help="Number of days to look back for PRs (default: 365)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit the number of repositories to process (for testing)",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Enable verbose output",
        )
        parser.add_argument(
            "--repos",
            type=str,
            default=None,
            help="Comma-separated list of repositories to process (e.g., 'OWASP-BLT/BLT,OWASP-BLT/BLT-Flutter')",
        )

    def handle(self, *args, **options):
        days = options["days"]
        limit = options["limit"]
        verbose = options["verbose"]
        repos_arg = options["repos"]

        self.stdout.write(f"Fetching closed PRs from the past {days} days for GSoC repositories")

        # Determine which repositories to process
        if repos_arg:
            # Process specific repositories
            all_repos = repos_arg.split(",")
            self.stdout.write(f"Processing specific repositories: {', '.join(all_repos)}")
        else:
            # Flatten the list of repositories from all projects
            all_repos = []
            for project, repos in GSOC25_PROJECTS.items():
                all_repos.extend(repos)

            # Remove duplicates
            all_repos = list(set(all_repos))

        if limit:
            all_repos = all_repos[:limit]
            self.stdout.write(f"Limited to {limit} repositories for testing")

        self.stdout.write(f"Found {len(all_repos)} repositories to process")

        total_prs_fetched = 0
        total_prs_added = 0

        for repo_full_name in all_repos:
            try:
                owner, repo_name = repo_full_name.split("/")

                # Check if the repository exists in our database
                repo = self.get_or_create_repo(owner, repo_name)

                # Fetch closed PRs from the past year
                prs = self.fetch_closed_prs(owner, repo_name, days, verbose)

                # Save PRs to the database
                added_count = self.save_prs_to_db(repo, prs, verbose)

                total_prs_fetched += len(prs)
                total_prs_added += added_count

                self.stdout.write(f"Processed {repo_full_name}: Fetched {len(prs)} PRs, Added {added_count} new PRs")

            except Exception as e:
                logger.error(f"Error processing repository {repo_full_name}: {str(e)}", exc_info=True)
                self.stdout.write(self.style.ERROR(f"Error processing repository {repo_full_name}: {str(e)}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Completed fetching PRs for GSoC repositories. "
                f"Total fetched: {total_prs_fetched}, Total added: {total_prs_added}"
            )
        )

    def get_or_create_repo(self, owner, repo_name):
        """
        Get or create a repository in our database.
        """
        # Try to find the repository by name
        repo = Repo.objects.filter(name=repo_name).first()

        if not repo:
            # If not found, try to find by repo_url
            repo_url = f"https://github.com/{owner}/{repo_name}"
            repo = Repo.objects.filter(repo_url=repo_url).first()

            if not repo:
                # If still not found, create a new repository
                self.stdout.write(f"Creating new repository: {owner}/{repo_name}")

                # Fetch repository data from GitHub API
                headers = {"Accept": "application/vnd.github.v3+json"}
                if settings.GITHUB_TOKEN:
                    headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

                url = f"https://api.github.com/repos/{owner}/{repo_name}"
                response = requests.get(url, headers=headers)
                response.raise_for_status()

                repo_data = response.json()

                # Create the repository
                repo = Repo(
                    name=repo_name,
                    repo_url=repo_url,
                    description=repo_data.get("description", ""),
                    stars=repo_data.get("stargazers_count", 0),
                    forks=repo_data.get("forks_count", 0),
                    open_issues=repo_data.get("open_issues_count", 0),
                    watchers=repo_data.get("watchers_count", 0),
                    primary_language=repo_data.get("language"),
                    is_owasp_repo=owner.upper() == "OWASP",
                )
                repo.save()

        return repo

    def fetch_closed_prs(self, owner, repo_name, days, verbose=False):
        """
        Fetch closed pull requests from GitHub API.
        Only fetches PRs from the past specified number of days.
        """
        prs = []
        page = 1
        per_page = 100

        # Calculate date for filtering
        since_date = timezone.now() - timedelta(days=days)
        since_date_str = since_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        headers = {"Accept": "application/vnd.github.v3+json"}
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

        while True:
            url = (
                f"https://api.github.com/repos/{owner}/{repo_name}/pulls"
                f"?state=closed&per_page={per_page}&page={page}&sort=updated&direction=desc"
                f"&since={since_date_str}"
            )

            if verbose:
                self.stdout.write(f"Fetching PRs from: {url}")

            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()

                data = response.json()
                if not data:
                    break

                prs.extend(data)

                # Check if we've reached the last page
                if len(data) < per_page:
                    break

                page += 1

            except Exception as e:
                logger.error(f"Error fetching PRs for {owner}/{repo_name}: {str(e)}", exc_info=True)
                self.stdout.write(self.style.ERROR(f"Error fetching PRs for {owner}/{repo_name}: {str(e)}"))
                break

        if verbose:
            self.stdout.write(f"Fetched {len(prs)} PRs for {owner}/{repo_name}")

        return prs

    @transaction.atomic
    def save_prs_to_db(self, repo, prs, verbose=False):
        """
        Save pull requests to the database.
        Returns the number of new PRs added.
        """
        added_count = 0

        for pr in prs:
            # Check if PR already exists in the database
            if GitHubIssue.objects.filter(issue_id=pr["id"]).exists():
                if verbose:
                    self.stdout.write(f"PR {pr['number']} already exists in the database")
                continue

            # Parse dates
            created_at = datetime.strptime(pr["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC)
            updated_at = datetime.strptime(pr["updated_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC)

            closed_at = None
            if pr["closed_at"]:
                closed_at = datetime.strptime(pr["closed_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC)

            merged_at = None
            is_merged = False
            if pr["merged_at"]:
                merged_at = datetime.strptime(pr["merged_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC)
                is_merged = True

            # Try to find the user profile
            user_profile = None
            if pr["user"] and pr["user"]["html_url"]:
                user_profile = UserProfile.objects.filter(github_url=pr["user"]["html_url"]).first()

            # Create the GitHubIssue
            github_issue = GitHubIssue(
                issue_id=pr["id"],
                title=pr["title"],
                body=pr["body"] or "",
                state=pr["state"],
                type="pull_request",
                created_at=created_at,
                updated_at=updated_at,
                closed_at=closed_at,
                merged_at=merged_at,
                is_merged=is_merged,
                url=pr["html_url"],
                repo=repo,
                user_profile=user_profile,
            )
            github_issue.save()

            added_count += 1

            if verbose:
                self.stdout.write(f"Added PR #{pr['number']}: {pr['title']}")

        return added_count
