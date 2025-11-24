import logging
from datetime import datetime
from urllib.parse import urlparse

import pytz
import requests
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.management.base import BaseCommand
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
        verbose = options.get("verbose", False)  # Use verbose flag from options
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

    def fetch_and_save_prs(self, repo, owner, repo_name, since_date, verbose=False):
        """
        Fetch closed pull requests from GitHub API using Search API for server-side filtering.
        Returns a tuple of (total_prs_fetched, total_prs_added, total_prs_updated).
        """
        total_prs_fetched = 0
        total_prs_added = 0
        total_prs_updated = 0

        since_date_str = since_date.strftime("%Y-%m-%d")

        self.stdout.write(f"Fetching merged PRs for {owner}/{repo_name} since {since_date_str}")

        # Set up headers for GitHub API
        headers = {"Accept": "application/vnd.github.v3+json"}
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

        # Use GitHub Search API for server-side filtering by merge date
        page = 1
        per_page = 100
        reached_end = False

        while not reached_end:
            # Search API allows filtering by merged date
            url = (
                f"https://api.github.com/search/issues"
                f"?q=repo:{owner}/{repo_name}+type:pr+is:merged+merged:>={since_date_str}"
                f"&per_page={per_page}&page={page}&sort=updated&order=desc"
            )

            if verbose:
                self.stdout.write(f"Fetching PRs from: {url}")

            try:
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()

                result = response.json()
                data = result.get("items", [])

                if not data:
                    if verbose:
                        self.stdout.write(f"No more PRs found for {owner}/{repo_name} on page {page}")
                    reached_end = True
                    break

                if verbose:
                    self.stdout.write(f"Fetched {len(data)} merged PRs from page {page}")

                # Process this page of PRs
                prs_added, prs_updated = self.save_prs_to_db(repo, data, since_date, verbose)
                total_prs_fetched += len(data)
                total_prs_added += prs_added
                total_prs_updated += prs_updated

                # Check if we've reached the last page
                if len(data) < per_page:
                    if verbose:
                        self.stdout.write(f"Reached last page ({page}) for {owner}/{repo_name}")
                    reached_end = True
                    break

                page += 1

            except Exception as e:
                logger.error(f"Error fetching PRs for {owner}/{repo_name}: {str(e)}", exc_info=True)
                self.stdout.write(self.style.ERROR(f"Error fetching PRs for {owner}/{repo_name}: {str(e)}"))
                break

        self.stdout.write(f"Fetched {total_prs_fetched} PRs, Added {total_prs_added}, Updated {total_prs_updated}")

        return total_prs_fetched, total_prs_added, total_prs_updated

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
            GitHubIssue.objects.filter(
                repo=repo, issue_id__in=[pr["number"] for pr in prs if "pull_request" in pr]
            ).values_list("issue_id", flat=True)
        )

        # Collect all contributor data first
        contributor_github_ids = []
        contributor_data_map = {}

        for pr in prs:
            if not pr.get("pull_request", {}).get("merged_at"):
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
            # Search API returns issues, check if it has pull_request key
            if "pull_request" not in pr:
                continue

            # Get merged_at from pull_request object
            pr_data = pr.get("pull_request", {})
            merged_at_str = pr_data.get("merged_at")

            # Skip PRs that aren't merged
            if not merged_at_str:
                skipped_not_merged += 1
                continue

            # Parse dates
            created_at = datetime.strptime(pr["created_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC)
            updated_at = datetime.strptime(pr["updated_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC)
            closed_at = (
                datetime.strptime(pr["closed_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC)
                if pr.get("closed_at")
                else None
            )
            merged_at = datetime.strptime(merged_at_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.UTC)

            # Skip PRs that were merged before the since_date
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
        for pr_number, data in prs_to_update:
            GitHubIssue.objects.filter(repo=repo, issue_id=pr_number).update(
                **{k: v for k, v in data.items() if k not in ["repo", "issue_id"]}
            )

        # Bulk add contributors to repo (M2M relationship)
        if existing_contributors:
            repo.contributor.add(*existing_contributors.values())

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

        # Get the reviews URL from the PR data (Search API returns pull_request.url)
        pr_obj = pr_data.get("pull_request", {})
        reviews_url = pr_obj.get("url")

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
