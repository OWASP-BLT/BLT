import time
from datetime import datetime

import pytz
import requests
from django.conf import settings
from django.db import transaction

from website.management.base import LoggedBaseCommand
from website.models import Contributor, GitHubComment, GitHubIssue, Repo, UserProfile


class Command(LoggedBaseCommand):
    help = "Fetch GitHub comments from issues, PRs, and discussions for the BLT repository"

    def add_arguments(self, parser):
        parser.add_argument(
            "--repo",
            type=str,
            default="OWASP-BLT/BLT",
            help="GitHub repository in format 'owner/repo' (default: OWASP-BLT/BLT)",
        )
        parser.add_argument(
            "--all-repos",
            action="store_true",
            help="Fetch comments from all repositories in the database",
        )

    def handle(self, *args, **kwargs):
        repo_name = kwargs.get("repo")
        all_repos = kwargs.get("all_repos")

        if not hasattr(settings, "GITHUB_TOKEN") or not settings.GITHUB_TOKEN:
            self.stdout.write(
                self.style.ERROR("GITHUB_TOKEN not configured in settings. Please set it to use the GitHub API.")
            )
            return

        if all_repos:
            repos = Repo.objects.filter(repo_url__icontains="github.com")
            self.stdout.write(self.style.SUCCESS(f"Fetching comments from {repos.count()} repositories"))
            for repo_obj in repos:
                try:
                    # Extract owner/repo from URL
                    repo_url_parts = repo_obj.repo_url.strip("/").split("/")
                    if len(repo_url_parts) >= 2:
                        owner_repo = f"{repo_url_parts[-2]}/{repo_url_parts[-1]}"
                        self.fetch_comments_for_repo(owner_repo, repo_obj)
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"Error processing repo {repo_obj.name}: {str(e)}"))
        else:
            # Get or create Repo object for the specified repository
            repo_obj = None
            try:
                repo_obj = Repo.objects.get(repo_url__icontains=repo_name)
            except Repo.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(f"Repo {repo_name} not found in database, creating with limited data")
                )
                # Create minimal repo entry
                repo_obj = Repo.objects.create(
                    name=repo_name.split("/")[-1],
                    repo_url=f"https://github.com/{repo_name}",
                )
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error finding repo: {str(e)}"))
                return

            self.fetch_comments_for_repo(repo_name, repo_obj)

        self.stdout.write(self.style.SUCCESS("Finished fetching GitHub comments"))

    def fetch_comments_for_repo(self, repo_name, repo_obj):
        """Fetch comments for a specific repository."""
        self.stdout.write(self.style.SUCCESS(f"\nProcessing repository: {repo_name}"))

        headers = {
            "Authorization": f"token {settings.GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        }

        # Fetch issues and PRs
        issues_and_prs = self.fetch_issues_and_prs(repo_name, headers, repo_obj)

        # Fetch comments for each issue/PR
        total_comments = 0
        for item in issues_and_prs:
            comments_count = self.fetch_comments_for_item(item, repo_name, headers, repo_obj)
            total_comments += comments_count
            time.sleep(0.5)  # Rate limiting

        self.stdout.write(self.style.SUCCESS(f"Fetched {total_comments} comments from {repo_name}"))

    def fetch_issues_and_prs(self, repo_name, headers, repo_obj):
        """Fetch all issues and PRs from the repository."""
        items = []
        page = 1
        per_page = 100

        while True:
            url = f"https://api.github.com/repos/{repo_name}/issues?state=all&per_page={per_page}&page={page}"
            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                data = response.json()

                if not data:
                    break

                items.extend(data)
                self.stdout.write(
                    self.style.SUCCESS(f"Fetched page {page} of issues/PRs ({len(data)} items, total: {len(items)})")
                )

                page += 1
                time.sleep(0.5)  # Rate limiting

            except requests.exceptions.RequestException as e:
                self.stdout.write(self.style.ERROR(f"Error fetching issues/PRs: {str(e)}"))
                break

        return items

    def fetch_comments_for_item(self, item, repo_name, headers, repo_obj):
        """Fetch comments for a specific issue or PR."""
        issue_number = item["number"]
        comments_url = item["comments_url"]

        if item.get("comments", 0) == 0:
            return 0

        page = 1
        comments_count = 0

        while True:
            url = f"{comments_url}?per_page=100&page={page}"
            try:
                response = requests.get(url, headers=headers, timeout=30)
                response.raise_for_status()
                comments = response.json()

                if not comments:
                    break

                for comment in comments:
                    try:
                        self.save_comment(comment, item, repo_obj)
                        comments_count += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f"Error saving comment {comment.get('id')}: {str(e)}")
                        )

                page += 1
                time.sleep(0.3)  # Rate limiting

            except requests.exceptions.RequestException as e:
                self.stdout.write(
                    self.style.ERROR(f"Error fetching comments for issue #{issue_number}: {str(e)}")
                )
                break

        return comments_count

    def save_comment(self, comment, issue_item, repo_obj):
        """Save a comment to the database."""
        comment_id = comment["id"]

        # Check if comment already exists
        if GitHubComment.objects.filter(comment_id=comment_id).exists():
            return

        # Determine if this is an issue or PR
        comment_type = "pull_request" if "pull_request" in issue_item else "issue"

        # Try to find the associated GitHubIssue
        github_issue = None
        try:
            github_issue = GitHubIssue.objects.get(issue_id=issue_item["number"], repo=repo_obj)
        except GitHubIssue.DoesNotExist:
            pass

        # Try to find user profile by GitHub username
        user_profile = None
        contributor = None
        github_username = comment["user"]["login"]

        try:
            user_profile = UserProfile.objects.get(user__username=github_username)
        except UserProfile.DoesNotExist:
            # Try to find by contributor
            try:
                contributor = Contributor.objects.get(github_id=comment["user"]["id"])
            except Contributor.DoesNotExist:
                pass

        # Parse dates
        created_at = datetime.strptime(comment["created_at"], "%Y-%m-%dT%H:%M:%SZ")
        created_at = pytz.UTC.localize(created_at)

        updated_at = datetime.strptime(comment["updated_at"], "%Y-%m-%dT%H:%M:%SZ")
        updated_at = pytz.UTC.localize(updated_at)

        # Create the comment
        with transaction.atomic():
            GitHubComment.objects.create(
                comment_id=comment_id,
                github_issue=github_issue,
                user_profile=user_profile,
                contributor=contributor,
                body=comment.get("body", ""),
                comment_type=comment_type,
                created_at=created_at,
                updated_at=updated_at,
                url=comment["html_url"],
                repo=repo_obj,
            )
