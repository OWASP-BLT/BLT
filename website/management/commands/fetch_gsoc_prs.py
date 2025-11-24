import logging
from datetime import datetime
from urllib.parse import urlparse

import pytz
import requests
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from website.models import Contributor, GitHubIssue, Repo, UserProfile
from website.views.constants import GSOC25_PROJECTS

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch closed pull requests from GitHub repositories merged in the last 6 months"

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

        # Fetch PRs from the last 6 months
        since_date = timezone.now() - relativedelta(months=6)
        since_date_str = since_date.strftime("%Y-%m-%d")

        self.stdout.write(f"Fetching closed PRs merged in the last 6 months (since {since_date_str})")

        # Determine which repositories to process
        if repos_arg:
            # Process specific repositories
            all_repos = repos_arg.split(",")
            self.stdout.write(f"Processing specific repositories: {', '.join(all_repos)}")
        else:
            # Auto-discover BLT repos from database, or use GSOC25_PROJECTS as fallback
            blt_repos_from_db = Repo.objects.filter(
                Q(repo_url__startswith="https://github.com/OWASP-BLT/")
                | Q(repo_url__startswith="https://github.com/owasp-blt/")
            )

            if blt_repos_from_db.exists():
                # Extract owner/repo from database URLs using proper URL parsing
                all_repos = []
                for repo in blt_repos_from_db:
                    try:
                        # Parse URL properly to validate domain
                        parsed = urlparse(repo.repo_url)

                        # Validate that this is actually a github.com URL
                        if parsed.netloc.lower() == "github.com":
                            # Extract path and clean it
                            path = parsed.path.strip("/").replace(".git", "")
                            parts = path.split("/")

                            # Validate format (should be owner/repo)
                            if len(parts) >= 2:
                                owner_repo = "/".join(parts[:2])  # Take only owner/repo, ignore extra paths
                                all_repos.append(owner_repo)
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"Invalid URL format for repo {repo.name}: {str(e)}"))
                        continue

                self.stdout.write(f"Auto-discovered {len(all_repos)} BLT repositories from database")
            else:
                # Fallback to GSOC25_PROJECTS
                all_repos = []
                for _project, repos in GSOC25_PROJECTS.items():
                    all_repos.extend(repos)
                # Remove duplicates
                all_repos = list(set(all_repos))
                self.stdout.write("Using GSOC25_PROJECTS (no BLT repos found in database)")

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

                # Fetch closed PRs since the specified date
                prs_fetched, prs_added, prs_updated = self.fetch_and_save_prs(
                    repo, owner, repo_name, since_date, verbose
                )

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

    def fetch_and_save_prs(self, repo, owner, repo_name, since_date, verbose=False):
        """
        Fetch closed pull requests from GitHub API and save them to the database.
        Returns a tuple of (total_prs_fetched, total_prs_added, total_prs_updated).
        """
        total_prs_fetched = 0
        total_prs_added = 0
        total_prs_updated = 0

        since_date_str = since_date.strftime("%Y-%m-%d")

        self.stdout.write(f"Fetching closed PRs for {owner}/{repo_name}")
        self.stdout.write(f"Will filter for PRs merged since {since_date_str}")
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
            # Note: The /pulls endpoint doesn't support 'since' parameter
            # We filter by merged_at date locally after fetching
            url = (
                f"https://api.github.com/repos/{owner}/{repo_name}/pulls"
                f"?state=closed&per_page={per_page}&page={page}&sort=updated&direction=desc"
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
                prs_added, prs_updated = self.save_prs_to_db(repo, data, since_date, verbose)
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
                repo=repo, type="pull_request", is_merged=True, merged_at__gte=since_date
            )
            merged_prs = merged_prs_query.count()
            self.stdout.write(f"Total merged PRs in database: {merged_prs}")

        return total_prs_fetched, total_prs_added, total_prs_updated

    @transaction.atomic
    def save_prs_to_db(self, repo, prs, since_date, verbose=False):
        """
        Save pull requests to the database.
        Returns the number of new PRs added and updated.
        """
        added_count = 0
        updated_count = 0
        skipped_count = 0
        skipped_not_merged = 0
        skipped_old_prs = 0

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

            # Skip PRs that were merged before the since_date
            if merged_at and merged_at < since_date:
                skipped_old_prs += 1
                if verbose:
                    self.stdout.write(f"PR {pr['number']} was merged before {since_date}, skipping")
                continue

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
                user_type = pr["user"].get("type", "User")

                # Skip bot accounts using GitHub API type field
                if user_type == "Bot":
                    if verbose:
                        self.stdout.write(f"Skipping bot account: {github_username}")
                    continue

                # Fallback check for bot naming patterns
                if github_username.endswith("[bot]"):
                    if verbose:
                        self.stdout.write(f"Skipping bot account (by name): {github_username}")
                    continue

                try:
                    contributor, created = Contributor.objects.get_or_create(
                        github_id=github_id,
                        defaults={
                            "name": github_username,
                            "github_url": github_url,
                            "avatar_url": avatar_url,
                            "contributor_type": user_type,
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

                # Fetch reviews for this PR
                self.fetch_and_save_reviews(github_issue, pr, verbose)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error saving PR #{pr['number']}: {str(e)}"))
                skipped_count += 1

        self.stdout.write(f"Skipped {skipped_count} PRs due to errors")
        self.stdout.write(f"Skipped {skipped_not_merged} PRs that are not merged")
        if skipped_old_prs > 0:
            self.stdout.write(f"Skipped {skipped_old_prs} PRs merged before {since_date.strftime('%Y-%m-%d')}")
        self.stdout.write(f"Added {added_count} new PRs to the database")
        self.stdout.write(f"Updated {updated_count} existing PRs in the database")

        return added_count, updated_count

    def fetch_and_save_reviews(self, github_issue, pr_data, verbose=False):
        """
        Fetch and save reviews for a pull request.
        """
        from website.models import GitHubReview

        # Get the reviews URL from the PR data
        reviews_url = pr_data.get("url")
        if not reviews_url:
            return

        reviews_url = reviews_url + "/reviews"

        headers = {"Accept": "application/vnd.github.v3+json"}
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

        try:
            response = requests.get(reviews_url, headers=headers, timeout=10)
            if response.status_code != 200:
                return

            reviews_data = response.json()
            if not isinstance(reviews_data, list):
                return

            for review in reviews_data:
                if not review.get("user"):
                    continue

                reviewer_login = review["user"].get("login")
                reviewer_github_id = review["user"].get("id")
                reviewer_github_url = review["user"].get("html_url")
                reviewer_avatar_url = review["user"].get("avatar_url")
                reviewer_type = review["user"].get("type", "User")

                # Skip bot accounts using GitHub API type field
                if reviewer_type == "Bot":
                    continue

                # Fallback check for bot naming patterns
                if reviewer_login and reviewer_login.endswith("[bot]"):
                    continue

                # Get or create reviewer contributor
                reviewer_contributor = None
                if reviewer_github_id:
                    reviewer_contributor, created = Contributor.objects.get_or_create(
                        github_id=reviewer_github_id,
                        defaults={
                            "name": reviewer_login,
                            "github_url": reviewer_github_url,
                            "avatar_url": reviewer_avatar_url,
                            "contributor_type": reviewer_type,
                            "contributions": 1,
                        },
                    )

                    if not created:
                        # Increment review count for existing contributors
                        reviewer_contributor.contributions += 1
                        reviewer_contributor.save()

                # Check if reviewer has a UserProfile
                reviewer_profile = None
                if reviewer_github_url:
                    reviewer_profile = UserProfile.objects.filter(github_url=reviewer_github_url).first()

                # Create or update the review
                GitHubReview.objects.update_or_create(
                    review_id=review["id"],
                    defaults={
                        "pull_request": github_issue,
                        "reviewer": reviewer_profile,
                        "reviewer_contributor": reviewer_contributor,
                        "body": review.get("body", ""),
                        "state": review["state"],
                        "submitted_at": datetime.strptime(review["submitted_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                            tzinfo=pytz.UTC
                        ),
                        "url": review["html_url"],
                    },
                )

                if verbose:
                    self.stdout.write(f"  Saved review by {reviewer_login}")

        except (requests.RequestException, ValueError) as e:
            if verbose:
                self.stdout.write(self.style.WARNING(f"  Error fetching reviews: {str(e)}"))
