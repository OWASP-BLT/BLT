import logging
from datetime import datetime

import pytz
import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from website.models import Contributor, GitHubIssue, Repo, UserProfile
from website.views.constants import GSOC25_PROJECTS

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch closed pull requests from GitHub repositories listed on the GSoC page since 2024-11-11"

    def add_arguments(self, parser):
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
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Reset the last_pr_page_processed counter and start from the beginning",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        verbose = True  # Always use verbose mode for debugging
        repos_arg = options["repos"]
        reset = options["reset"]

        self.stdout.write("Fetching closed PRs since 2024-11-11 for GSoC repositories")

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
        total_prs_updated = 0

        for repo_full_name in all_repos:
            try:
                owner, repo_name = repo_full_name.split("/")

                # Check if the repository exists in our database
                repo = self.get_or_create_repo(owner, repo_name)

                # Reset the last_pr_page_processed if requested
                if reset:
                    repo.last_pr_page_processed = 0
                    repo.save()
                    self.stdout.write(f"Reset last_pr_page_processed for {repo_full_name}")

                # Fetch closed PRs since 2024-11-11
                prs_fetched, prs_added, prs_updated = self.fetch_and_save_prs(repo, owner, repo_name, verbose)

                total_prs_fetched += prs_fetched
                total_prs_added += prs_added
                total_prs_updated += prs_updated

                self.stdout.write(
                    f"Processed {repo_full_name}: Fetched {prs_fetched} PRs, "
                    f"Added {prs_added} new PRs, Updated {prs_updated} existing PRs"
                )

            except Exception as e:
                logger.error(f"Error processing repository {repo_full_name}: {str(e)}", exc_info=True)
                self.stdout.write(self.style.ERROR(f"Error processing repository {repo_full_name}: {str(e)}"))

        self.stdout.write(
            self.style.SUCCESS(
                f"Completed fetching PRs for GSoC repositories. "
                f"Total fetched: {total_prs_fetched}, "
                f"Total added: {total_prs_added}, "
                f"Total updated: {total_prs_updated}"
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
                    last_pr_page_processed=0,
                )
                repo.save()

        return repo

    def fetch_and_save_prs(self, repo, owner, repo_name, verbose=False):
        """
        Fetch closed pull requests from GitHub API and save them to the database.
        Returns a tuple of (total_prs_fetched, total_prs_added, total_prs_updated).
        """
        total_prs_fetched = 0
        total_prs_added = 0
        total_prs_updated = 0

        # Fixed start date: 2024-11-11
        since_date = timezone.make_aware(datetime(2024, 11, 11))
        since_date_str = since_date.strftime("%Y-%m-%dT%H:%M:%SZ")

        self.stdout.write(f"Fetching PRs since {since_date_str} for {owner}/{repo_name}")
        self.stdout.write(f"Current date: {timezone.now().strftime('%Y-%m-%dT%H:%M:%SZ')}")
        self.stdout.write(f"Starting from page {repo.last_pr_page_processed + 1}")

        # Set up headers for GitHub API
        headers = {"Accept": "application/vnd.github.v3+json"}
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"
            self.stdout.write("Using GitHub token for authentication")
        else:
            self.stdout.write("No GitHub token found, using unauthenticated requests (rate limits may apply)")

        # Start from the last processed page + 1
        page = repo.last_pr_page_processed + 1
        per_page = 100
        reached_end = False

        while not reached_end:
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
                    self.stdout.write(f"No more PRs found for {owner}/{repo_name} on page {page}")
                    reached_end = True
                    break

                self.stdout.write(f"Fetched {len(data)} PRs from page {page}")

                # Check if any PRs are merged
                merged_count = sum(1 for pr in data if pr.get("merged_at") is not None)
                self.stdout.write(f"Found {merged_count} merged PRs on page {page}")

                # Process this page of PRs
                prs_added, prs_updated = self.save_prs_to_db(repo, data, verbose)
                total_prs_fetched += len(data)
                total_prs_added += prs_added
                total_prs_updated += prs_updated

                # Update the repository's last processed page
                repo.last_pr_page_processed = page
                repo.last_pr_fetch_date = timezone.now()
                repo.save()

                # Check if we've reached the last page
                if len(data) < per_page:
                    self.stdout.write(f"Reached last page ({page}) for {owner}/{repo_name}")
                    reached_end = True
                    break

                page += 1

            except Exception as e:
                logger.error(f"Error fetching PRs for {owner}/{repo_name}: {str(e)}", exc_info=True)
                self.stdout.write(self.style.ERROR(f"Error fetching PRs for {owner}/{repo_name}: {str(e)}"))
                break

        if verbose:
            self.stdout.write(f"Fetched {total_prs_fetched} PRs for {owner}/{repo_name}")
            merged_prs_query = GitHubIssue.objects.filter(
                repo=repo, type="pull_request", is_merged=True, created_at__gte=since_date
            )
            merged_prs = merged_prs_query.count()
            self.stdout.write(f"Total merged PRs in database: {merged_prs}")

        return total_prs_fetched, total_prs_added, total_prs_updated

    @transaction.atomic
    def save_prs_to_db(self, repo, prs, verbose=False):
        """
        Save pull requests to the database.
        Returns the number of new PRs added and updated.
        """
        added_count = 0
        updated_count = 0
        skipped_count = 0
        skipped_not_merged = 0

        self.stdout.write(f"Processing {len(prs)} PRs for {repo.name}")

        for pr in prs:
            # Skip PRs that aren't merged
            if not pr.get("merged_at"):
                skipped_not_merged += 1
                if verbose:
                    self.stdout.write(f"PR {pr['number']} is not merged, skipping")
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
            contributor = None
            github_url = None

            if pr["user"] and pr["user"]["html_url"]:
                # Get or create a Contributor record
                github_url = pr["user"]["html_url"]
                github_id = pr["user"]["id"]
                github_username = pr["user"]["login"]
                avatar_url = pr["user"]["avatar_url"]

                # Skip bot accounts
                if github_username.endswith("[bot]") or "bot" in github_username.lower():
                    if verbose:
                        self.stdout.write(f"Skipping bot account: {github_username}")
                    continue

                try:
                    contributor, created = Contributor.objects.get_or_create(
                        github_id=github_id,
                        defaults={
                            "name": github_username,
                            "github_url": github_url,
                            "avatar_url": avatar_url,
                            "contributor_type": "User",
                            "contributions": 1,
                        },
                    )

                    if not created:
                        # Update the contributions count
                        contributor.contributions += 1
                        contributor.save()

                    if verbose:
                        if created:
                            self.stdout.write(f"Created new contributor: {github_username}")
                        else:
                            self.stdout.write(
                                f"Updated contributor: {github_username}, contributions: {contributor.contributions}"
                            )

                    # Also try to find a matching UserProfile
                    user_profile = UserProfile.objects.filter(github_url=github_url).first()

                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"Error creating/updating contributor {github_username}: {str(e)}")
                    )

            # Prepare the data for the GitHubIssue
            issue_data = {
                "title": pr["title"],
                "body": pr["body"] or "",
                "state": pr["state"],
                "type": "pull_request",
                "created_at": created_at,
                "updated_at": updated_at,
                "closed_at": closed_at,
                "merged_at": merged_at,
                "is_merged": is_merged,
                "url": pr["html_url"],
                "user_profile": user_profile,
                "contributor": contributor,
            }

            # Try to get the existing issue or create a new one
            try:
                # Use issue_id and repo as the lookup fields to match the unique_together constraint
                github_issue, created = GitHubIssue.objects.update_or_create(
                    issue_id=pr["number"],  # Use number instead of id
                    repo=repo,
                    defaults=issue_data,
                )

                if created:
                    added_count += 1
                    if verbose:
                        self.stdout.write(f"Added PR #{pr['number']}: {pr['title']}")
                else:
                    updated_count += 1
                    if verbose:
                        self.stdout.write(f"Updated PR #{pr['number']}: {pr['title']}")

                # Add the repo to the contributor's repos if not already there
                if contributor and repo:
                    # The relationship is defined in the Repo model, so we need to add the contributor to the repo
                    repo.contributor.add(contributor)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error saving PR #{pr['number']}: {str(e)}"))
                skipped_count += 1

        self.stdout.write(f"Skipped {skipped_count} PRs due to errors")
        self.stdout.write(f"Skipped {skipped_not_merged} PRs that are not merged")
        self.stdout.write(f"Added {added_count} new PRs to the database")
        self.stdout.write(f"Updated {updated_count} existing PRs in the database")

        return added_count, updated_count
