from collections import defaultdict
from datetime import datetime
from urllib.parse import quote_plus

import requests
from django.conf import settings
from django.core.management import CommandError
from django.db import transaction
from django.utils import timezone

from website.management.base import LoggedBaseCommand
from website.models import Contributor, GitHubIssue, GitHubReview, Repo, UserProfile


class Command(LoggedBaseCommand):
    help = "Fetches and updates GitHub issue and review data for users with GitHub profiles"

    def add_arguments(self, parser):
        parser.add_argument(
            "--all-blt-repos",
            action="store_true",
            help="Also fetch all PRs from BLT repos (not just from BLT users)",
        )

    def handle(self, *_, **options):
        fetch_all_blt = options.get("all_blt_repos", False)

        # Fetch PRs from the last 6 months
        from dateutil.relativedelta import relativedelta

        since_date = timezone.now() - relativedelta(months=6)
        since_date_str = since_date.strftime("%Y-%m-%d")

        users_with_github = UserProfile.objects.exclude(github_url="").exclude(github_url=None)
        user_count = users_with_github.count()

        self.stdout.write(f"Found {user_count} users with GitHub profiles")

        # If no users with GitHub URLs, just fetch BLT repos directly
        if user_count == 0:
            self.stdout.write(self.style.WARNING("No users with GitHub URLs found."))
            self.stdout.write("Fetching PRs from BLT repositories instead...")

            from django.core.management import call_command

            try:
                call_command("fetch_gsoc_prs")
                self.stdout.write(self.style.SUCCESS("Successfully fetched BLT repo PRs!"))
            except CommandError as e:
                self.stdout.write(self.style.ERROR(f"Error fetching BLT repo PRs: {e!s}"))
            return

        self.stdout.write(f"Fetching PRs merged in the last 6 months (since {since_date_str})")
        self.stdout.write("-" * 50)

        merged_pr_counts = defaultdict(int)

        for index, user in enumerate(users_with_github, 1):
            self.stdout.write(f"[{index}/{user_count}] Processing user: {user.github_url}")

            github_username = user.github_url.split("/")[-1]
            query = f"author:{github_username} type:pr"
            encoded_query = quote_plus(query)
            api_url = f"https://api.github.com/search/issues?q={encoded_query}&per_page=100&page=1"

            headers = {"Accept": "application/vnd.github.v3+json", "Authorization": f"token {settings.GITHUB_TOKEN}"}

            all_prs = []

            # Handle pagination for pull requests
            while api_url:
                try:
                    response = requests.get(api_url, headers=headers, timeout=(3, 20))
                    response.raise_for_status()
                    prs_data = response.json()

                    all_prs.extend(prs_data.get("items", []))

                    # Check if there's a "next" page in headers
                    api_url = response.links.get("next", {}).get("url")

                except requests.exceptions.RequestException as e:
                    self.stdout.write(self.style.ERROR(f"Error fetching data for {github_username}: {e!s}"))
                    break  # Stop fetching if an error occurs

            pr_count = len(all_prs)
            self.stdout.write(f"Found {pr_count} pull requests")

            skipped_old_prs = 0

            with transaction.atomic():
                for pr in all_prs:
                    repo_full_name = pr["repository_url"].split("repos/")[-1]
                    repo_name = repo_full_name.split("/")[-1].lower()
                    # Construct the full GitHub repo URL to uniquely identify the repository
                    github_repo_url = f"https://github.com/{repo_full_name}"

                    try:
                        merged = True if pr["pull_request"].get("merged_at") else False

                        # Skip PRs that aren't merged
                        if not merged:
                            continue

                        # Parse merged_at date and skip if before since_date
                        merged_at = timezone.make_aware(
                            datetime.strptime(pr["pull_request"]["merged_at"], "%Y-%m-%dT%H:%M:%SZ")
                        )
                        if merged_at < since_date:
                            skipped_old_prs += 1
                            continue
                        # Use repo_url (which is unique) instead of name (which can have duplicates)
                        repo = Repo.objects.get(repo_url=github_repo_url)

                        # Get or create contributor record
                        try:
                            # Get user details from GitHub API
                            user_api_url = pr["user"]["url"]
                            user_response = requests.get(user_api_url, headers=headers, timeout=(3, 10))
                            user_response.raise_for_status()
                            user_data = user_response.json()

                            # Find or create contributor
                            contributor, created = Contributor.objects.get_or_create(
                                github_id=user_data["id"],
                                defaults={
                                    "name": user_data["login"],
                                    "github_url": user_data["html_url"],
                                    "avatar_url": user_data["avatar_url"],
                                    "contributor_type": user_data["type"],
                                    "contributions": 1,
                                },
                            )

                            if not created:
                                # Update existing contributor data
                                contributor.name = user_data["login"]
                                contributor.github_url = user_data["html_url"]
                                contributor.avatar_url = user_data["avatar_url"]
                                contributor.contributions += 1
                                contributor.save()

                            # Add contributor to repo
                            repo.contributor.add(contributor)

                        except CommandError as e:
                            self.stdout.write(self.style.WARNING(f"Error creating contributor: {e!s}"))
                            contributor = None

                        # Create or update the pull request
                        github_issue, created = GitHubIssue.objects.update_or_create(
                            issue_id=pr["number"],
                            repo=repo,  # Add repo to the lookup to ensure uniqueness
                            defaults={
                                "title": pr["title"],
                                "body": pr.get("body", ""),
                                "state": pr["state"],
                                "type": "pull_request",
                                "created_at": timezone.make_aware(
                                    datetime.strptime(pr["created_at"], "%Y-%m-%dT%H:%M:%SZ")
                                ),
                                "updated_at": timezone.make_aware(
                                    datetime.strptime(pr["updated_at"], "%Y-%m-%dT%H:%M:%SZ")
                                ),
                                "closed_at": timezone.make_aware(
                                    datetime.strptime(pr["closed_at"], "%Y-%m-%dT%H:%M:%SZ")
                                )
                                if pr.get("closed_at")
                                else None,
                                "merged_at": timezone.make_aware(
                                    datetime.strptime(pr["pull_request"]["merged_at"], "%Y-%m-%dT%H:%M:%SZ")
                                )
                                if merged
                                else None,
                                "is_merged": merged,
                                "url": pr["html_url"],
                                "user_profile": user,
                                "contributor": contributor,  # Link to contributor
                            },
                        )

                        if merged:
                            merged_pr_counts[user.id] += 1

                        # Fetch reviews for this pull request
                        reviews_url = pr["pull_request"]["url"] + "/reviews"
                        try:
                            reviews_response = requests.get(reviews_url, headers=headers, timeout=10)
                            reviews_response.raise_for_status()  # Check for HTTP errors
                            reviews_data = reviews_response.json()

                            # Store ALL reviews (not just from BLT users)
                            if isinstance(reviews_data, list):
                                for review in reviews_data:
                                    if not review.get("user"):
                                        continue

                                    reviewer_login = review["user"].get("login")
                                    reviewer_github_id = review["user"].get("id")
                                    reviewer_github_url = review["user"].get("html_url")
                                    reviewer_avatar_url = review["user"].get("avatar_url")
                                    reviewer_type = review["user"].get("type", "User")

                                    # Skip bot accounts using GitHub API type first
                                    if reviewer_type == "Bot":
                                        continue

                                    # Fallback check for bot naming patterns
                                    if reviewer_login and reviewer_login.endswith("[bot]"):
                                        continue

                                    # Get or create reviewer contributor
                                    reviewer_contributor = None
                                    if reviewer_github_id:
                                        reviewer_contributor, _ = Contributor.objects.get_or_create(
                                            github_id=reviewer_github_id,
                                            defaults={
                                                "name": reviewer_login,
                                                "github_url": reviewer_github_url,
                                                "avatar_url": reviewer_avatar_url,
                                                "contributor_type": reviewer_type,
                                                "contributions": 0,
                                            },
                                        )

                                    # Check if reviewer has a UserProfile
                                    reviewer_profile = None
                                    if reviewer_github_url:
                                        reviewer_profile = UserProfile.objects.filter(
                                            github_url=reviewer_github_url
                                        ).first()

                                    # Create or update the review
                                    GitHubReview.objects.update_or_create(
                                        review_id=review["id"],
                                        defaults={
                                            "pull_request": github_issue,
                                            "reviewer": reviewer_profile,
                                            "reviewer_contributor": reviewer_contributor,
                                            "body": review.get("body", ""),
                                            "state": review["state"],
                                            "submitted_at": timezone.make_aware(
                                                datetime.strptime(review["submitted_at"], "%Y-%m-%dT%H:%M:%SZ")
                                            ),
                                            "url": review["html_url"],
                                        },
                                    )
                        except requests.exceptions.RequestException as e:
                            self.stdout.write(self.style.ERROR(f"Error fetching reviews for PR {pr['number']}: {e!s}"))
                            continue

                    except Repo.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Repo not found in database: {github_repo_url}. Not storing this issue in database."
                            )
                        )
                        continue

            if skipped_old_prs > 0:
                self.stdout.write(f"Skipped {skipped_old_prs} PRs merged before {since_date.strftime('%Y-%m-%d')}")
            self.stdout.write(self.style.SUCCESS(f"Successfully updated PRs and reviews for {github_username}"))

        # Bulk update merged PR count
        UserProfile.objects.bulk_update(
            [UserProfile(id=user_id, merged_pr_count=count) for user_id, count in merged_pr_counts.items()],
            ["merged_pr_count"],
        )

        # Assign contribution ranks
        sorted_users = UserProfile.objects.exclude(github_url="").exclude(github_url=None).order_by("-merged_pr_count")

        for rank, user in enumerate(sorted_users, start=1):
            user.contribution_rank = rank

        UserProfile.objects.bulk_update(sorted_users, ["contribution_rank"])

        self.stdout.write("-" * 50)
        self.stdout.write(self.style.SUCCESS("GitHub data fetch completed!"))

        # Optionally fetch all PRs from BLT repos (not just from BLT users)
        if fetch_all_blt:
            from django.core.management import call_command

            self.stdout.write("")
            self.stdout.write("=" * 50)
            self.stdout.write(self.style.SUCCESS("Fetching all PRs from BLT repos..."))
            self.stdout.write("=" * 50)
            try:
                call_command("fetch_gsoc_prs")
                self.stdout.write(self.style.SUCCESS("Successfully fetched all BLT repo PRs!"))
            except CommandError as e:
                self.stdout.write(self.style.ERROR(f"Error fetching BLT repo PRs: {e!s}"))
