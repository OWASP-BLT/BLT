from collections import defaultdict
from datetime import datetime

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from website.management.base import LoggedBaseCommand
from website.models import Contributor, GitHubIssue, GitHubReview, Repo, UserProfile


class Command(LoggedBaseCommand):
    help = "Fetches and updates GitHub issue and review data for users with GitHub profiles"

    def handle(self, *args, **options):
        users_with_github = UserProfile.objects.exclude(github_url="").exclude(github_url=None)
        user_count = users_with_github.count()

        self.stdout.write(self.style.SUCCESS(f"Found {user_count} users with GitHub profiles"))
        self.stdout.write("-" * 50)

        merged_pr_counts = defaultdict(int)

        for index, user in enumerate(users_with_github, 1):
            self.stdout.write(f"[{index}/{user_count}] Processing user: {user.github_url}")

            github_username = user.github_url.split("/")[-1]
            api_url = f"https://api.github.com/search/issues?q=author:{github_username}+type:pr&per_page=100&page=1"

            headers = {"Accept": "application/vnd.github.v3+json", "Authorization": f"token {settings.GITHUB_TOKEN}"}

            all_prs = []

            # Handle pagination for pull requests
            while api_url:
                try:
                    response = requests.get(api_url, headers=headers)
                    response.raise_for_status()
                    prs_data = response.json()

                    all_prs.extend(prs_data.get("items", []))

                    # Check if there's a "next" page in headers
                    api_url = response.links.get("next", {}).get("url")

                except requests.exceptions.RequestException as e:
                    self.stdout.write(self.style.ERROR(f"Error fetching data for {github_username}: {str(e)}"))
                    break  # Stop fetching if an error occurs

            pr_count = len(all_prs)
            self.stdout.write(f"Found {pr_count} pull requests")

            with transaction.atomic():
                for pr in all_prs:
                    repo_full_name = pr["repository_url"].split("repos/")[-1]
                    repo_name = repo_full_name.split("/")[-1].lower()

                    try:
                        merged = True if pr["pull_request"].get("merged_at") else False
                        repo = Repo.objects.get(name__iexact=repo_name)

                        # Get or create contributor record
                        try:
                            # Get user details from GitHub API
                            user_api_url = pr["user"]["url"]
                            user_response = requests.get(user_api_url, headers=headers)
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

                        except Exception as e:
                            self.stdout.write(self.style.WARNING(f"Error creating contributor: {str(e)}"))
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
                            reviews_response = requests.get(reviews_url, headers=headers)
                            reviews_response.raise_for_status()  # Check for HTTP errors
                            reviews_data = reviews_response.json()

                            # Store reviews made by ANY user (not just the PR author)
                            if isinstance(reviews_data, list):
                                for review in reviews_data:
                                    reviewer_login = review.get("user", {}).get("login")
                                    if reviewer_login:
                                        # Try to find the reviewer's UserProfile
                                        try:
                                            reviewer_profile = UserProfile.objects.filter(
                                                github_url__icontains=reviewer_login
                                            ).first()

                                            if reviewer_profile:
                                                GitHubReview.objects.update_or_create(
                                                    review_id=review["id"],
                                                    defaults={
                                                        "pull_request": github_issue,
                                                        "reviewer": reviewer_profile,  # The actual reviewer, not the PR author
                                                        "body": review.get("body", ""),
                                                        "state": review["state"],
                                                        "submitted_at": timezone.make_aware(
                                                            datetime.strptime(review["submitted_at"], "%Y-%m-%dT%H:%M:%SZ")
                                                        ),
                                                        "url": review["html_url"],
                                                    },
                                                )
                                        except Exception as e:
                                            self.stdout.write(
                                                self.style.WARNING(f"Could not find UserProfile for reviewer {reviewer_login}: {str(e)}")
                                            )
                        except requests.exceptions.RequestException as e:
                            self.stdout.write(
                                self.style.ERROR(f"Error fetching reviews for PR {pr['number']}: {str(e)}")
                            )
                            continue

                    except Repo.DoesNotExist:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Repo not found in database: {repo_name}. Not storing this issue in database."
                            )
                        )
                        continue

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
