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

from website.models import Contributor, GitHubComment, GitHubIssue, UserProfile

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fetch comments for existing GitHub issues and pull requests using parallel requests"

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
        parser.add_argument(
            "--months",
            type=int,
            default=6,
            help="Number of months of comments to fetch (default: 6)",
        )
        parser.add_argument(
            "--repo",
            type=str,
            help="Specific repository URL to fetch comments from (e.g., https://github.com/OWASP-BLT/BLT)",
        )

    def handle(self, *args, **options):
        verbose = options.get("verbose", False)
        max_workers = options.get("workers", 30)
        months = options.get("months", 6)
        repo_url = options.get("repo")

        # Only fetch comments from the last N months
        since_date = timezone.now() - relativedelta(months=months)
        self.stdout.write(f"Fetching comments created since {since_date.strftime('%Y-%m-%d')}")

        # Build queryset for issues and PRs
        queryset = GitHubIssue.objects.filter(created_at__gte=since_date)

        # Filter by specific repo if provided, otherwise use all OWASP-BLT repos
        if repo_url:
            queryset = queryset.filter(repo__repo_url=repo_url)
            self.stdout.write(f"Filtering for repository: {repo_url}")
        else:
            queryset = queryset.filter(
                Q(repo__repo_url__startswith="https://github.com/OWASP-BLT/")
                | Q(repo__repo_url__startswith="https://github.com/owasp-blt/")
            )
            self.stdout.write("Fetching comments from all OWASP-BLT repositories")

        # Get issues and PRs - use values_list for efficiency
        issues = list(queryset.values_list("id", "issue_id", "url", "repo__name", "type").order_by("-created_at"))

        total_issues = len(issues)
        self.stdout.write(f"Found {total_issues} issues/PRs to process with {max_workers} parallel workers")

        if not total_issues:
            self.stdout.write(self.style.WARNING("No issues or PRs found to process"))
            return

        # Set up headers for GitHub API
        headers = {"Accept": "application/vnd.github.v3+json"}
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"
        else:
            self.stdout.write(
                self.style.WARNING(
                    "GITHUB_TOKEN not configured. API rate limits will be lower. "
                    "Configure GITHUB_TOKEN in settings for better performance."
                )
            )

        # Collect all comments first with parallel requests
        self.stdout.write("Fetching comments from GitHub API...")
        all_comments_data = []
        all_github_ids = set()
        all_github_urls = set()

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_issue = {
                executor.submit(self.fetch_issue_comments, issue_id, issue_url, headers, since_date): (
                    issue_id,
                    issue_number,
                )
                for issue_id, issue_number, issue_url, _, _ in issues
            }

            completed = 0
            for future in as_completed(future_to_issue):
                completed += 1
                if completed % 20 == 0:
                    self.stdout.write(f"Progress: {completed}/{total_issues} issues/PRs")

                issue_id, issue_number = future_to_issue[future]
                try:
                    comments = future.result()
                    if comments:
                        for comment in comments:
                            if comment.get("user"):
                                github_id = comment["user"]["id"]
                                github_url = comment["user"]["html_url"]
                                commenter_type = comment["user"].get("type", "User")
                                commenter_login = comment["user"]["login"]

                                # Skip bots early
                                if commenter_type == "Bot" or commenter_login.endswith("[bot]"):
                                    continue

                                # Filter out other common bots
                                if any(
                                    bot in commenter_login.lower()
                                    for bot in ["copilot", "dependabot", "github-actions", "renovate"]
                                ):
                                    continue

                                all_comments_data.append((issue_id, comment))
                                all_github_ids.add(github_id)
                                all_github_urls.add(github_url)
                except Exception as e:
                    if verbose:
                        logger.error(f"Error fetching comments for issue #{issue_number}: {e}")

        self.stdout.write(f"Fetched {len(all_comments_data)} comments from {total_issues} issues/PRs")

        if not all_comments_data:
            self.stdout.write(self.style.WARNING("No comments found"))
            return

        # Bulk fetch contributors and user profiles
        self.stdout.write("Processing contributors...")
        contributor_map = {c.github_id: c for c in Contributor.objects.filter(github_id__in=all_github_ids)}

        userprofile_map = {up.github_url: up for up in UserProfile.objects.filter(github_url__in=all_github_urls)}

        # Bulk create missing contributors
        missing_contributors = {}
        for issue_id, comment in all_comments_data:
            github_id = comment["user"]["id"]
            if github_id not in contributor_map and github_id not in missing_contributors:
                missing_contributors[github_id] = Contributor(
                    github_id=github_id,
                    name=comment["user"]["login"],
                    github_url=comment["user"]["html_url"],
                    avatar_url=comment["user"]["avatar_url"],
                    contributor_type=comment["user"].get("type", "User"),
                    contributions=0,
                )

        if missing_contributors:
            Contributor.objects.bulk_create(missing_contributors.values(), ignore_conflicts=True)
            # Refresh contributor map
            contributor_map.update(
                {c.github_id: c for c in Contributor.objects.filter(github_id__in=missing_contributors.keys())}
            )

        # Get existing comment IDs to determine create vs update
        self.stdout.write("Preparing database operations...")
        existing_comment_ids = set(
            GitHubComment.objects.filter(
                comment_id__in=[comment["id"] for _, comment in all_comments_data]
            ).values_list("comment_id", flat=True)
        )

        # Pre-fetch all issue objects to avoid N+1 queries
        issue_ids = list(set(issue_id for issue_id, _ in all_comments_data))
        issue_objects_map = {issue.id: issue for issue in GitHubIssue.objects.filter(id__in=issue_ids)}

        # Bulk create/update comments
        comments_to_create = []
        comments_to_update_data = {}

        for issue_id, comment in all_comments_data:
            github_id = comment["user"]["id"]
            github_url = comment["user"]["html_url"]
            comment_id = comment["id"]

            contributor = contributor_map.get(github_id)
            user_profile = userprofile_map.get(github_url)
            issue_obj = issue_objects_map.get(issue_id)

            if not issue_obj:
                continue

            # Parse timestamps
            created_at = self.parse_github_datetime(comment.get("created_at"))
            updated_at = self.parse_github_datetime(comment.get("updated_at"))

            if comment_id in existing_comment_ids:
                # Store data for updating existing comments
                comments_to_update_data[comment_id] = {
                    "issue": issue_obj,
                    "commenter": user_profile,
                    "commenter_contributor": contributor,
                    "body": comment.get("body", ""),
                    "updated_at": updated_at,
                    "url": comment["html_url"],
                }
            else:
                # Create new comment object
                comments_to_create.append(
                    GitHubComment(
                        comment_id=comment_id,
                        issue=issue_obj,
                        commenter=user_profile,
                        commenter_contributor=contributor,
                        body=comment.get("body", ""),
                        created_at=created_at,
                        updated_at=updated_at,
                        url=comment["html_url"],
                    )
                )

        # Perform bulk operations
        created_count = 0
        updated_count = 0

        if comments_to_create:
            self.stdout.write(f"Creating {len(comments_to_create)} new comments...")
            GitHubComment.objects.bulk_create(comments_to_create, ignore_conflicts=True)
            created_count = len(comments_to_create)

        if comments_to_update_data:
            self.stdout.write(f"Updating {len(comments_to_update_data)} existing comments...")
            # Fetch existing comments from database with their PKs
            existing_comments = GitHubComment.objects.filter(comment_id__in=comments_to_update_data.keys())
            comments_to_update = []
            for comment_obj in existing_comments:
                update_data = comments_to_update_data[comment_obj.comment_id]
                comment_obj.issue = update_data["issue"]
                comment_obj.commenter = update_data["commenter"]
                comment_obj.commenter_contributor = update_data["commenter_contributor"]
                comment_obj.body = update_data["body"]
                comment_obj.updated_at = update_data["updated_at"]
                comment_obj.url = update_data["url"]
                comments_to_update.append(comment_obj)

            if comments_to_update:
                GitHubComment.objects.bulk_update(
                    comments_to_update,
                    ["issue", "commenter", "commenter_contributor", "body", "updated_at", "url"],
                )
                updated_count = len(comments_to_update)

        self.stdout.write(
            self.style.SUCCESS(f"Successfully processed {created_count} created, {updated_count} updated comments")
        )

    def fetch_issue_comments(self, issue_id, issue_url, headers, since_date):
        """
        Fetch comments for a specific issue or pull request.
        """
        # Extract owner and repo from URL
        # URL format: https://github.com/owner/repo/issues/number or https://github.com/owner/repo/pull/number
        parts = issue_url.split("/")
        if len(parts) < 7:
            return []

        owner = parts[3]
        repo = parts[4]
        issue_number = parts[6]

        # GitHub API endpoint for comments (works for both issues and PRs)
        api_url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments"

        params = {
            "per_page": 100,
            "since": since_date.isoformat(),
        }

        all_comments = []

        try:
            while api_url:
                response = requests.get(api_url, headers=headers, params=params, timeout=10)
                response.raise_for_status()

                comments = response.json()
                all_comments.extend(comments)

                # Check for pagination
                if "next" in response.links:
                    api_url = response.links["next"]["url"]
                    params = {}  # Clear params as URL will have them
                else:
                    api_url = None

        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching comments for issue #{issue_number}: {e}")
            return []

        return all_comments

    def parse_github_datetime(self, datetime_str):
        """
        Parse a GitHub datetime string to a timezone-aware datetime object.
        """
        if not datetime_str:
            return timezone.now()

        try:
            dt = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%SZ")
            return dt.replace(tzinfo=pytz.UTC)
        except (ValueError, TypeError):
            return timezone.now()
