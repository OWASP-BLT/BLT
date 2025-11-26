import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import pytz
import requests
from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from website.models import Contributor, GitHubIssue, GitHubReview, UserProfile

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch reviews for existing pull requests using parallel requests"

    def add_arguments(self, parser):
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Enable verbose output",
        )
        parser.add_argument(
            "--workers",
            type=int,
            default=30,
            help="Number of parallel workers (default: 30)",
        )

    def handle(self, *args, **options):
        verbose = options.get("verbose", False)
        max_workers = options.get("workers", 30)

        # Only fetch reviews for PRs merged in the last 6 months
        since_date = timezone.now() - relativedelta(months=6)
        self.stdout.write(f"Fetching reviews for PRs merged since {since_date.strftime('%Y-%m-%d')}")

        # Get PRs from BLT repos only - use values_list for efficiency
        prs = list(
            GitHubIssue.objects.filter(
                type="pull_request",
                is_merged=True,
                merged_at__gte=since_date,
            )
            .filter(
                Q(repo__repo_url__startswith="https://github.com/OWASP-BLT/")
                | Q(repo__repo_url__startswith="https://github.com/owasp-blt/")
            )
            .values_list("id", "issue_id", "url", "repo__name")
            .order_by("-merged_at")
        )

        total_prs = len(prs)
        self.stdout.write(f"Found {total_prs} PRs to process with {max_workers} parallel workers")

        # Set up headers for GitHub API
        headers = {"Accept": "application/vnd.github.v3+json"}
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

        # Collect all reviews first with parallel requests
        self.stdout.write("Fetching reviews from GitHub API...")
        all_reviews_data = []
        all_github_ids = set()
        all_github_urls = set()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_pr = {
                executor.submit(self.fetch_pr_reviews, pr_id, pr_url, headers): (pr_id, pr_number)
                for pr_id, pr_number, pr_url, _ in prs
            }

            completed = 0
            for future in as_completed(future_to_pr):
                completed += 1
                if completed % 20 == 0:
                    self.stdout.write(f"Progress: {completed}/{total_prs} PRs")

                pr_id, pr_number = future_to_pr[future]
                try:
                    reviews = future.result()
                    if reviews:
                        for review in reviews:
                            if review.get("user"):
                                github_id = review["user"]["id"]
                                github_url = review["user"]["html_url"]
                                reviewer_type = review["user"].get("type", "User")
                                reviewer_login = review["user"]["login"]

                                # Skip bots early
                                if reviewer_type == "Bot" or reviewer_login.endswith("[bot]"):
                                    continue

                                all_reviews_data.append((pr_id, review))
                                all_github_ids.add(github_id)
                                all_github_urls.add(github_url)
                except Exception as e:
                    if verbose:
                        logger.error(f"Error fetching reviews for PR #{pr_number}: {e}")

        self.stdout.write(f"Fetched {len(all_reviews_data)} reviews from {total_prs} PRs")

        if not all_reviews_data:
            self.stdout.write(self.style.WARNING("No reviews found"))
            return

        # Bulk fetch contributors and user profiles
        self.stdout.write("Processing contributors...")
        contributor_map = {c.github_id: c for c in Contributor.objects.filter(github_id__in=all_github_ids)}

        userprofile_map = {up.github_url: up for up in UserProfile.objects.filter(github_url__in=all_github_urls)}

        # Bulk create missing contributors
        missing_contributors = {}
        for pr_id, review in all_reviews_data:
            github_id = review["user"]["id"]
            if github_id not in contributor_map and github_id not in missing_contributors:
                missing_contributors[github_id] = Contributor(
                    github_id=github_id,
                    name=review["user"]["login"],
                    github_url=review["user"]["html_url"],
                    avatar_url=review["user"]["avatar_url"],
                    contributor_type=review["user"].get("type", "User"),
                    contributions=0,
                )

        if missing_contributors:
            Contributor.objects.bulk_create(missing_contributors.values(), ignore_conflicts=True)
            # Refresh contributor map
            contributor_map.update(
                {c.github_id: c for c in Contributor.objects.filter(github_id__in=missing_contributors.keys())}
            )

        # Get existing review IDs to determine create vs update
        self.stdout.write("Preparing database operations...")
        existing_review_ids = set(
            GitHubReview.objects.filter(review_id__in=[review["id"] for _, review in all_reviews_data]).values_list(
                "review_id", flat=True
            )
        )

        # Pre-fetch all PR objects to avoid N+1 queries
        pr_ids = list(set(pr_id for pr_id, _ in all_reviews_data))
        pr_objects_map = {pr.id: pr for pr in GitHubIssue.objects.filter(id__in=pr_ids)}

        # Bulk create/update reviews
        reviews_to_create = []
        reviews_to_update = []

        for pr_id, review in all_reviews_data:
            # Skip if PR doesn't exist
            pull_request_obj = pr_objects_map.get(pr_id)
            if not pull_request_obj:
                continue

            reviewer_github_id = review["user"]["id"]
            reviewer_github_url = review["user"]["html_url"]

            reviewer_contributor = contributor_map.get(reviewer_github_id)
            reviewer_profile = userprofile_map.get(reviewer_github_url)

            # Parse submitted_at safely (can be null for PENDING reviews)
            submitted_at = None
            if review.get("submitted_at"):
                try:
                    submitted_at = datetime.strptime(review["submitted_at"], "%Y-%m-%dT%H:%M:%SZ").replace(
                        tzinfo=pytz.UTC
                    )
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid submitted_at for review {review['id']}: {review.get('submitted_at')}")
                    continue  # Skip reviews with invalid dates
            else:
                # Skip PENDING reviews without submitted_at
                continue

            review_data = {
                "pull_request": pull_request_obj,
                "reviewer": reviewer_profile,
                "reviewer_contributor": reviewer_contributor,
                "body": review.get("body", "")[:1000],  # Truncate long bodies
                "state": review["state"],
                "submitted_at": submitted_at,
                "url": review["html_url"],
            }

            if review["id"] in existing_review_ids:
                reviews_to_update.append((review["id"], review_data))
            else:
                reviews_to_create.append(GitHubReview(review_id=review["id"], **review_data))

        # Bulk create
        if reviews_to_create:
            self.stdout.write(f"Creating {len(reviews_to_create)} new reviews...")
            GitHubReview.objects.bulk_create(reviews_to_create, batch_size=500, ignore_conflicts=True)

        # Bulk update (only if there are updates)
        if reviews_to_update:
            self.stdout.write(f"Updating {len(reviews_to_update)} existing reviews...")
            # Use bulk update instead of individual updates
            reviews_to_update_objs = []
            for review_id, data in reviews_to_update:
                try:
                    review_obj = GitHubReview.objects.get(review_id=review_id)
                    for key, value in data.items():
                        setattr(review_obj, key, value)
                    reviews_to_update_objs.append(review_obj)
                except GitHubReview.DoesNotExist:
                    pass

            if reviews_to_update_objs:
                GitHubReview.objects.bulk_update(
                    reviews_to_update_objs,
                    ["pull_request", "reviewer", "reviewer_contributor", "body", "state", "submitted_at", "url"],
                    batch_size=500,
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Completed! Added {len(reviews_to_create)} reviews, " f"Updated {len(reviews_to_update)} reviews"
            )
        )

    def fetch_pr_reviews(self, pr_id, pr_url, headers):
        """Fetch reviews for a single PR"""
        pr_url_parts = pr_url.replace("https://github.com/", "").split("/")
        if len(pr_url_parts) < 4:
            return []

        owner = pr_url_parts[0]
        repo_name = pr_url_parts[1]
        pr_num = pr_url_parts[3]

        reviews_url = f"https://api.github.com/repos/{owner}/{repo_name}/pulls/{pr_num}/reviews"

        try:
            response = requests.get(reviews_url, headers=headers, timeout=3)
            if response.status_code == 200:
                reviews_data = response.json()
                if isinstance(reviews_data, list):
                    return reviews_data
        except Exception:
            pass  # Silently fail for speed

        return []
