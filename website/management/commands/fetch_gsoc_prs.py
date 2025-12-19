import logging
import time
from datetime import datetime
from urllib.parse import urlparse

import pytz
import requests
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime

from website.models import Contributor, GitHubIssue, Repo, UserProfile
from website.views.constants import GSOC25_PROJECTS

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch closed pull requests from GitHub repositories merged in the last 6 months"

    def parse_github_datetime(self, value):
        """
        Parse GitHub API ISO 8601 datetime string to timezone-aware UTC datetime.
        Returns None if value is falsy.
        """
        if not value:
            return None
        dt = parse_datetime(value)
        if dt and dt.tzinfo is None:
            dt = dt.replace(tzinfo=pytz.UTC)
        return dt

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

        # (Backward compatible)
        parser.add_argument(
            "--since-date",
            type=str,
            default=None,
            help="Fetch PRs merged after this date (YYYY-MM-DD). Default: 6 months ago.",
        )

        parser.add_argument(
            "--rate-check-interval",
            type=int,
            default=10,
            help="Check rate limit every N pages (default: 10; use smaller for long backfills).",
        )
        parser.add_argument(
            "--rate-limit-threshold",
            type=int,
            default=500,
            help="Pause when remaining requests drop below this threshold (default: 500).",
        )

        # configurable 403 retry behavior
        parser.add_argument(
            "--max-retries",
            type=int,
            default=5,
            help="Maximum consecutive retries for 403 responses (default: 5).",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        verbose = options.get("verbose", False)  # Use verbose flag from options
        repos_arg = options["repos"]
        reset = options["reset"]

        # configurable rate & retry options
        rate_check_interval = options.get("rate_check_interval", 10)
        rate_limit_threshold = options.get("rate_limit_threshold", 500)
        max_retries = options.get("max_retries", 5)

        # EARLY VALIDATION (prevents runtime crashes)
        if rate_check_interval <= 0:
            raise ValueError("--rate-check-interval must be a positive integer")

        if rate_limit_threshold < 0:
            raise ValueError("--rate-limit-threshold must be a non-negative integer")

        if max_retries < 0:
            raise ValueError("--max-retries must be greater than or equal to 0")

        # safer since-date handling
        since_date_arg = options.get("since_date")

        if since_date_arg:
            date_obj = parse_date(since_date_arg)
            if not date_obj:
                raise ValueError(f"Invalid --since-date value: {since_date_arg}. Use YYYY-MM-DD.")
            since_date = datetime.combine(date_obj, datetime.min.time()).replace(tzinfo=pytz.UTC)
            self.stdout.write(f"Fetching closed PRs merged since {since_date_arg}")
        else:
            since_date = timezone.now() - relativedelta(months=6)
            self.stdout.write(
                f"Fetching closed PRs merged in the last 6 months (since {since_date.strftime('%Y-%m-%d')})"
            )

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
                    repo,
                    owner,
                    repo_name,
                    since_date,
                    verbose,
                    rate_check_interval=rate_check_interval,
                    rate_limit_threshold=rate_limit_threshold,
                    max_retries=max_retries,
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
                response = requests.get(url, headers=headers, timeout=10)
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

    def fetch_and_save_prs(
        self,
        repo,
        owner,
        repo_name,
        since_date,
        verbose=False,
        rate_check_interval=10,
        rate_limit_threshold=500,
        max_retries=5,
    ):
        total_prs_fetched = 0
        total_prs_added = 0
        total_prs_updated = 0

        since_date_str = since_date.strftime("%Y-%m-%d")
        self.stdout.write(f"Fetching merged PRs for {owner}/{repo_name} since {since_date_str}")

        headers = {"Accept": "application/vnd.github.v3+json"}
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

        page = 1
        per_page = 100
        reached_end = False
        retry_count = 0
        backoff_base = 60
        start_time = time.time()

        while not reached_end:
            url = (
                f"https://api.github.com/repos/{owner}/{repo_name}/pulls"
                f"?state=closed&per_page={per_page}&page={page}&sort=updated&direction=desc"
            )

            if verbose:
                self.stdout.write(f"Fetching PRs from: {url}")

            try:
                if page == 1 or page % rate_check_interval == 0:
                    self.check_and_wait_for_rate_limit(headers, verbose=verbose, threshold=rate_limit_threshold)

                response = requests.get(url, headers=headers, timeout=30)

                if response.status_code == 403:
                    retry_count += 1
                    if retry_count > max_retries:
                        msg = f"Max retries ({max_retries}) exceeded for {owner}/{repo_name} on page {page}"
                        self.stdout.write(self.style.ERROR(msg))
                        logger.error(msg)
                        break

                    retry_after = response.headers.get("Retry-After")
                    if retry_after:
                        wait_time = int(retry_after)
                    else:
                        # Exponential backoff: 60, 120, 240, ...
                        wait_time = min(backoff_base * (2 ** (retry_count - 1)), 3600)

                    logger.warning(
                        f"403 rate limit for {owner}/{repo_name}, "
                        f"retry {retry_count}/{max_retries}, waiting {wait_time}s"
                    )
                    self.stdout.write(
                        self.style.WARNING(
                            f"403 rate limit (attempt {retry_count}/{max_retries}). " f"Waiting {wait_time}s..."
                        )
                    )
                    time.sleep(wait_time)
                    continue
                retry_count = 0
                response.raise_for_status()
                data = response.json()

                if not data:
                    if verbose:
                        self.stdout.write(f"No more PRs found for {owner}/{repo_name} on page {page}")
                    reached_end = True
                    break

                merged_prs = []
                for pr in data:
                    merged_at = self.parse_github_datetime(pr.get("merged_at"))  # uses helper
                    if merged_at and merged_at >= since_date:
                        merged_prs.append(pr)

                if merged_prs:
                    prs_added, prs_updated = self.save_prs_to_db(repo, merged_prs, since_date, verbose)

                    total_prs_fetched += len(merged_prs)
                    total_prs_added += prs_added
                    total_prs_updated += prs_updated

                if len(data) < per_page:
                    reached_end = True
                    break

                # progress log every 10 pages
                if page % 10 == 0:
                    elapsed = time.time() - start_time
                    if elapsed > 0:
                        self.stdout.write(
                            f"Progress: Page {page}, fetched {total_prs_fetched} PRs " f"(elapsed: {int(elapsed)}s)"
                        )

                page += 1
                time.sleep(2)

            except Exception as e:
                logger.error(f"Error fetching PRs for {owner}/{repo_name}: {str(e)}", exc_info=True)
                self.stdout.write(self.style.ERROR(f"Error fetching PRs for {owner}/{repo_name}: {str(e)}"))
                break

        self.stdout.write(f"Fetched {total_prs_fetched} PRs, Added {total_prs_added}, Updated {total_prs_updated}")

        return total_prs_fetched, total_prs_added, total_prs_updated

    def check_and_wait_for_rate_limit(self, headers, verbose=False, threshold=500):
        """
        Check GitHub API rate limit and wait if necessary.
        Always logs a warning when we have to sleep.
        """
        try:
            response = requests.get(
                "https://api.github.com/rate_limit",
                headers=headers,
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                core = data.get("resources", {}).get("core", {})
                remaining = core.get("remaining", 0)
                limit = core.get("limit", 5000)
                reset_time = core.get("reset", 0)

                if verbose:
                    reset_dt = datetime.fromtimestamp(reset_time, tz=pytz.UTC)
                    self.stdout.write(
                        f"Rate limit status: {remaining}/{limit} requests remaining "
                        f"(resets at {reset_dt.strftime('%H:%M:%S UTC')})"
                    )

                if remaining < threshold:
                    wait_seconds = max(reset_time - int(time.time()), 0) + 10
                    reset_dt = datetime.fromtimestamp(reset_time, tz=pytz.UTC)
                    logger.warning(
                        f"GitHub API rate limit low: {remaining}/{limit} remaining. "
                        f"Sleeping {wait_seconds}s until reset at {reset_dt}"
                    )
                    self.stdout.write(
                        self.style.WARNING(
                            f"Rate limit low: {remaining}/{limit} remaining. " f"Pausing for {wait_seconds}s..."
                        )
                    )
                    time.sleep(wait_seconds)
                    self.stdout.write(self.style.SUCCESS("Rate limit wait complete, resuming..."))

            else:
                logger.warning(
                    f"Rate limit check returned status {response.status_code}. " f"Response: {response.text[:200]}"
                )
                if verbose:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Rate limit check failed with status {response.status_code}, continuing anyway"
                        )
                    )

        except requests.RequestException as e:
            logger.warning(f"Failed to check rate limit: {str(e)}", exc_info=verbose)
            if verbose:
                self.stdout.write(self.style.WARNING(f"Could not check rate limit ({str(e)}), continuing anyway"))
        except Exception as e:
            logger.error(f"Unexpected error checking rate limit: {str(e)}", exc_info=True)
            if verbose:
                self.stdout.write(self.style.ERROR(f"Unexpected rate limit check error: {str(e)}"))

    def save_prs_to_db(self, repo, prs, since_date, verbose=False):
        """
        Save pull requests to the database using bulk operations.
        Returns the number of new PRs added and updated.
        """
        added_count = 0
        updated_count = 0
        skipped_not_merged = 0
        skipped_old_prs = 0

        if verbose:
            self.stdout.write(f"Processing {len(prs)} PRs for {repo.name}")

        # Pre-fetch existing PRs for this repo
        existing_pr_ids = set(
            GitHubIssue.objects.filter(repo=repo, issue_id__in=[pr["number"] for pr in prs]).values_list(
                "issue_id", flat=True
            )
        )

        # Collect all contributor data first
        contributor_github_ids = []
        contributor_data_map = {}

        for pr in prs:
            if not pr.get("merged_at"):
                continue
            if pr.get("user") and pr["user"].get("id"):
                github_id = pr["user"]["id"]
                user_type = pr["user"].get("type", "User")
                username = pr["user"]["login"]

                # Skip bots
                if user_type == "Bot" or username.endswith("[bot]"):
                    continue

                contributor_github_ids.append(github_id)
                contributor_data_map[github_id] = {
                    "name": username,
                    "github_url": pr["user"]["html_url"],
                    "avatar_url": pr["user"]["avatar_url"],
                    "contributor_type": user_type,
                }

        # Bulk fetch existing contributors
        existing_contributors = {
            c.github_id: c for c in Contributor.objects.filter(github_id__in=contributor_github_ids)
        }

        # Bulk create missing contributors
        new_contributors = []
        for github_id, data in contributor_data_map.items():
            if github_id not in existing_contributors:
                new_contributors.append(
                    Contributor(
                        github_id=github_id,
                        name=data["name"],
                        github_url=data["github_url"],
                        avatar_url=data["avatar_url"],
                        contributor_type=data["contributor_type"],
                        contributions=0,
                    )
                )

        if new_contributors:
            Contributor.objects.bulk_create(new_contributors, ignore_conflicts=True)
            # Refresh contributor cache
            existing_contributors = {
                c.github_id: c for c in Contributor.objects.filter(github_id__in=contributor_github_ids)
            }

        # Bulk fetch user profiles
        github_urls = [data["github_url"] for data in contributor_data_map.values()]
        userprofile_map = {up.github_url: up for up in UserProfile.objects.filter(github_url__in=github_urls)}

        # Prepare bulk create/update lists
        prs_to_create = []
        prs_to_update = []

        for pr in prs:
            # Get merged_at from pull_request object
            merged_at_str = pr.get("merged_at")

            # Skip PRs that aren't merged
            if not merged_at_str:
                skipped_not_merged += 1
                continue

            # Parse dates
            created_at = self.parse_github_datetime(pr.get("created_at"))
            updated_at = self.parse_github_datetime(pr.get("updated_at"))
            closed_at = self.parse_github_datetime(pr.get("closed_at"))
            merged_at = self.parse_github_datetime(merged_at_str)

            # Skip PRs that were merged before the since_date
            if not merged_at:
                skipped_not_merged += 1
                continue

            if merged_at < since_date:
                skipped_old_prs += 1
                continue

            # Get contributor and user profile from cache
            contributor = None
            user_profile = None

            if pr.get("user") and pr["user"].get("id"):
                github_id = pr["user"]["id"]
                github_url = pr["user"]["html_url"]
                user_type = pr["user"].get("type", "User")
                username = pr["user"]["login"]

                # Skip bots
                if user_type == "Bot" or username.endswith("[bot]"):
                    continue

                contributor = existing_contributors.get(github_id)
                user_profile = userprofile_map.get(github_url)

            # Prepare the data for the GitHubIssue
            issue_data = {
                "repo": repo,
                "issue_id": pr["number"],
                "title": pr["title"],
                "body": pr["body"] or "",
                "state": pr["state"],
                "type": "pull_request",
                "created_at": created_at,
                "updated_at": updated_at,
                "closed_at": closed_at,
                "merged_at": merged_at,
                "is_merged": True,
                "url": pr["html_url"],
                "user_profile": user_profile,
                "contributor": contributor,
            }

            # Check if PR exists
            if pr["number"] in existing_pr_ids:
                prs_to_update.append((pr["number"], issue_data))
                updated_count += 1
            else:
                prs_to_create.append(GitHubIssue(**issue_data))
                added_count += 1

        # Bulk create new PRs
        if prs_to_create:
            GitHubIssue.objects.bulk_create(prs_to_create, ignore_conflicts=True)

        # Bulk update existing PRs
        if prs_to_update:
            # Fetch existing PR objects
            pr_numbers_to_update = [pr_number for pr_number, _ in prs_to_update]
            existing_prs = {
                pr.issue_id: pr for pr in GitHubIssue.objects.filter(repo=repo, issue_id__in=pr_numbers_to_update)
            }

            # Update fields in memory
            prs_to_bulk_update = []
            for pr_number, data in prs_to_update:
                pr_obj = existing_prs.get(pr_number)
                if pr_obj:
                    # Update all fields except repo and issue_id
                    for key, value in data.items():
                        if key not in ["repo", "issue_id"]:
                            setattr(pr_obj, key, value)
                    prs_to_bulk_update.append(pr_obj)

            # Bulk update in one query
            if prs_to_bulk_update:
                GitHubIssue.objects.bulk_update(
                    prs_to_bulk_update,
                    [
                        "title",
                        "body",
                        "state",
                        "created_at",
                        "updated_at",
                        "closed_at",
                        "merged_at",
                        "is_merged",
                        "url",
                        "user_profile",
                        "contributor",
                    ],
                    batch_size=100,
                )

        # Bulk add contributors to repo (M2M relationship)
        if existing_contributors:
            existing_links = set(repo.contributor.values_list("github_id", flat=True))
            new_contributors_to_add = [c for c in existing_contributors.values() if c.github_id not in existing_links]

            if new_contributors_to_add:
                repo.contributor.add(*new_contributors_to_add)

        if verbose:
            if skipped_not_merged > 0:
                self.stdout.write(f"Skipped {skipped_not_merged} PRs that are not merged")
            if skipped_old_prs > 0:
                self.stdout.write(f"Skipped {skipped_old_prs} PRs merged before {since_date.strftime('%Y-%m-%d')}")

        self.stdout.write(f"Added {added_count} new PRs, Updated {updated_count} existing PRs")

        return added_count, updated_count

    def fetch_and_save_reviews(self, github_issue, pr_data, verbose=False):
        """
        Fetch and save reviews for a pull request.
        """
        from website.models import GitHubReview

        # Prefer pull_request.url (Search API shape), fall back to root url (REST /pulls)
        reviews_url = pr_data.get("pull_request", {}).get("url") or pr_data.get("url")

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

                # Skip reviews without submitted_at (e.g., PENDING reviews)
                submitted_at_str = review.get("submitted_at")
                if not submitted_at_str:
                    continue

                # Create or update the review
                GitHubReview.objects.update_or_create(
                    review_id=review["id"],
                    defaults={
                        "pull_request": github_issue,
                        "reviewer": reviewer_profile,
                        "reviewer_contributor": reviewer_contributor,
                        "body": review.get("body", ""),
                        "state": review["state"],
                        "submitted_at": self.parse_github_datetime(review.get("submitted_at")),
                        "url": review["html_url"],
                    },
                )

                if verbose:
                    self.stdout.write(f"  Saved review by {reviewer_login}")

        except (requests.RequestException, ValueError) as e:
            if verbose:
                self.stdout.write(self.style.WARNING(f"  Error fetching reviews: {str(e)}"))
