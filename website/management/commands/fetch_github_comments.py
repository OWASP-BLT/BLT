import logging
import time
from datetime import datetime

import requests
from django.conf import settings
from django.core.management.base import CommandError
from django.db import transaction
from django.db.models import F

from website.management.base import LoggedBaseCommand
from website.models import Contributor, GitHubComment, GitHubIssue, Repo, UserProfile

logger = logging.getLogger(__name__)


class Command(LoggedBaseCommand):
    help = "Fetch GitHub comments from repositories and populate the GitHubComment model for leaderboard tracking"

    def add_arguments(self, parser):
        parser.add_argument(
            "--repo_id",
            type=int,
            help="Specific repository ID to fetch comments from",
        )
        parser.add_argument(
            "--repo_slug",
            type=str,
            help="Repository slug to fetch comments from",
        )
        parser.add_argument(
            "--blt-only",
            action="store_true",
            help="Only fetch comments from BLT repository",
        )
        parser.add_argument(
            "--project-id",
            type=int,
            help="Project ID to fetch comments from all its repositories",
        )
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Fetch comments from last N days (default: 30)",
        )

    def handle(self, *args, **options):
        repo_id = options.get("repo_id")
        repo_slug = options.get("repo_slug")
        blt_only = options.get("blt_only")
        project_id = options.get("project_id")
        days = options.get("days")

        repos_to_fetch = []

        try:
            if blt_only:
                # Fetch comments from BLT repository
                repos_to_fetch = self.get_blt_repos()
                if not repos_to_fetch:
                    self.stdout.write(self.style.WARNING("BLT repository not found"))
                else:
                    self.stdout.write(f"Fetching comments from BLT repository: {repos_to_fetch[0].name}")
            elif repo_id:
                # Fetch comments from specific repository by ID
                try:
                    repo = Repo.objects.get(id=repo_id)
                    repos_to_fetch = [repo]
                except Repo.DoesNotExist:
                    raise CommandError(f"Repository with ID {repo_id} not found")
            elif repo_slug:
                # Fetch comments from specific repository by slug
                try:
                    repo = Repo.objects.get(slug=repo_slug)
                    repos_to_fetch = [repo]
                except Repo.DoesNotExist:
                    raise CommandError(f"Repository with slug {repo_slug} not found")
            elif project_id:
                # Fetch comments from all repositories in a project
                repos_to_fetch = Repo.objects.filter(project_id=project_id)
                if not repos_to_fetch.exists():
                    raise CommandError(f"No repositories found for project ID {project_id}")
                self.stdout.write(f"Fetching comments from {repos_to_fetch.count()} repositories in project")
            else:
                # Fetch from BLT by default
                repos_to_fetch = self.get_blt_repos()
                if not repos_to_fetch:
                    repos_to_fetch = Repo.objects.all()[:5]  # Fetch from first 5 repos if BLT not found
                    self.stdout.write("BLT repo not found, fetching from first 5 repositories")

            # Fetch comments for each repository
            for repo in repos_to_fetch:
                self.fetch_comments_for_repo(repo, days)

            self.stdout.write(self.style.SUCCESS("Successfully fetched GitHub comments"))

        except Exception as e:
            logger.error(f"Error fetching GitHub comments: {str(e)}")
            raise CommandError(f"Error: {str(e)}")

    def get_blt_repos(self):
        """Get BLT repository (OWASP-BLT/BLT)"""
        try:
            return [Repo.objects.get(name="BLT", is_main=True)]
        except Repo.DoesNotExist:
            # Try to find by URL pattern
            blt_repos = Repo.objects.filter(name="BLT", repo_url__contains="OWASP-BLT/BLT")
            if blt_repos.exists():
                return [blt_repos.first()]
            return []

    def fetch_comments_for_repo(self, repo, days=30):
        """Fetch comments for a specific repository from GitHub API"""
        self.stdout.write(f"Processing repository: {repo.name}")

        owner, repo_name = self.parse_github_url(repo.repo_url)

        # Get all GitHub issues/PRs for this repo
        github_issues = GitHubIssue.objects.filter(repo=repo).select_related("repo")

        if not github_issues.exists():
            self.stdout.write(self.style.WARNING(f"No GitHub issues found for {repo.name}"))
            return

        self.stdout.write(f"Found {github_issues.count()} issues/PRs to fetch comments from")

        headers = {
            "Authorization": f"token {settings.GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        }

        for issue in github_issues:
            self.fetch_comments_for_issue(issue, headers)
            time.sleep(0.2)  # Rate limiting

    def fetch_comments_for_issue(self, issue, headers):
        """Fetch comments for a specific GitHub issue"""
        try:
            # Extract owner and repo from issue URL
            parts = issue.url.split("/")
            owner = parts[3]
            repo_name = parts[4]
            issue_number = parts[6]

            # GitHub API endpoint for comments
            api_url = f"https://api.github.com/repos/{owner}/{repo_name}/issues/{issue_number}/comments"

            response = requests.get(api_url, headers=headers, params={"per_page": 100})

            if response.status_code == 403:
                reset_timestamp = int(response.headers.get("X-RateLimit-Reset", 0))
                sleep_time = max(reset_timestamp - time.time(), 0) + 1
                logger.warning(f"Rate limit exceeded. Waiting {sleep_time} seconds...")
                time.sleep(sleep_time)
                response = requests.get(api_url, headers=headers, params={"per_page": 100})

            if response.status_code != 200:
                logger.warning(f"Failed to fetch comments for issue {issue.issue_id}: {response.status_code}")
                return

            comments = response.json()

            if not comments:
                return

            # Process each comment
            for comment in comments:
                self.save_comment(issue, comment)

        except Exception as e:
            logger.error(f"Error fetching comments for issue {issue.issue_id}: {str(e)}")

    def save_comment(self, issue, comment_data):
        """Save a GitHub comment to the database"""
        try:
            with transaction.atomic():
                comment_id = comment_data.get("id")
                commenter_login = comment_data.get("user", {}).get("login", "Unknown")

                # Check if comment already exists
                if GitHubComment.objects.filter(comment_id=comment_id).exists():
                    return

                # Get or create Contributor
                commenter = None
                commenter_profile = None

                try:
                    commenter = Contributor.objects.get(github_url=comment_data["user"]["html_url"])
                except Contributor.DoesNotExist:
                    # Try to create it from API data
                    try:
                        commenter = Contributor.objects.create(
                            name=comment_data["user"].get("login", "Unknown"),
                            github_id=comment_data["user"].get("id", 0),
                            github_url=comment_data["user"].get("html_url", ""),
                            avatar_url=comment_data["user"].get("avatar_url", ""),
                            contributor_type=comment_data["user"].get("type", "User"),
                            contributions=0,
                        )
                    except Exception as e:
                        logger.warning(f"Could not create Contributor for {commenter_login}: {str(e)}")

                # Try to link to UserProfile
                try:
                    commenter_profile = UserProfile.objects.get(
                        github_url=comment_data["user"]["html_url"]
                    )
                except UserProfile.DoesNotExist:
                    # Try matching by GitHub username
                    try:
                        commenter_profile = UserProfile.objects.filter(
                            user__username__iexact=commenter_login
                        ).first()
                    except Exception:
                        pass

                # Create the comment record
                GitHubComment.objects.create(
                    comment_id=comment_id,
                    github_issue=issue,
                    repo=issue.repo,
                    commenter_login=commenter_login,
                    commenter=commenter,
                    commenter_profile=commenter_profile,
                    body=comment_data.get("body", ""),
                    comment_url=comment_data.get("html_url", ""),
                    created_at=datetime.fromisoformat(comment_data.get("created_at", "").replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(comment_data.get("updated_at", "").replace("Z", "+00:00")),
                )

                # Atomically increment the issue's comment count
                GitHubIssue.objects.filter(pk=issue.pk).update(comments_count=F("comments_count") + 1)

        except Exception as e:
            logger.error(f"Error saving comment {comment_data.get('id', 'unknown')}: {str(e)}")

    def parse_github_url(self, url):
        """Extract owner and repo name from GitHub URL"""
        url = url.rstrip("/")
        parts = url.split("/")
        return parts[-2], parts[-1]
