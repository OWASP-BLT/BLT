import logging
import time

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from website.models import Contributor, GitHubIssue, Repo

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Synchronize all contributors for a repository"

    def add_arguments(self, parser):
        parser.add_argument("--repo_id", type=int, help="Repository ID to sync")

    def handle(self, *args, **options):
        repo_id = options.get("repo_id")
        if not repo_id:
            return

        repo = Repo.objects.get(id=repo_id)
        owner_repo = repo.repo_url.rstrip("/").split("github.com/")[-1]

        headers = {
            "Authorization": f"token {settings.GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json",
        }

        # Get all contributors with pagination
        page = 1
        all_contributors = []

        while True:
            api_url = f"https://api.github.com/repos/{owner_repo}/contributors?anon=true&per_page=100&page={page}"
            response = requests.get(api_url, headers=headers)

            if response.status_code == 403:
                reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
                wait_time = reset_time - int(time.time())
                if wait_time > 0:
                    logger.info(f"Rate limit hit, waiting {wait_time} seconds")
                    time.sleep(wait_time)
                    continue

            if response.status_code != 200:
                break

            contributors_page = response.json()
            if not contributors_page:
                break

            all_contributors.extend(contributors_page)
            page += 1

            # Be nice to GitHub API
            time.sleep(1)

        # Batch create/update contributors
        contributors_by_login = {}
        for contrib_data in all_contributors:
            github_id = contrib_data.get("id")
            if not github_id:
                # skip if 'id' is missing
                continue
            contributor, created = Contributor.objects.update_or_create(
                github_id=github_id,
                defaults={
                    "name": contrib_data.get("login", "unknown"),
                    "github_url": contrib_data.get("html_url", ""),
                    "avatar_url": contrib_data.get("avatar_url", ""),
                    "contributions": contrib_data.get("contributions", 0),
                    "contributor_type": contrib_data.get("type", "User"),
                },
            )
            repo.contributor.add(contributor)

            # Store contributor by login for later use
            contributors_by_login[contrib_data.get("login")] = contributor

        repo.contributor_count = len(all_contributors)
        repo.save()

        # Link contributors to GitHubIssue records
        # Get all pull requests for this repo that don't have a contributor
        pull_requests = GitHubIssue.objects.filter(repo=repo, type="pull_request", contributor__isnull=True)

        logger.info(f"Found {pull_requests.count()} pull requests without contributors")

        for pr in pull_requests:
            try:
                # Extract GitHub username from URL
                # URL format: https://github.com/owner/repo/pull/123
                parts = pr.url.split("/")
                pr_number = parts[6]

                # Get PR details from GitHub API
                api_url = f"https://api.github.com/repos/{owner_repo}/pulls/{pr_number}"
                response = requests.get(api_url, headers=headers)

                if response.status_code != 200:
                    logger.warning(f"Failed to fetch PR #{pr_number}: {response.status_code}")
                    continue

                pr_data = response.json()
                github_username = pr_data["user"]["login"]

                # Find contributor by username
                contributor = contributors_by_login.get(github_username)

                if contributor:
                    # Link contributor to PR
                    pr.contributor = contributor

                    # Also check if PR is merged
                    if pr_data.get("merged_at") and not pr.is_merged:
                        pr.is_merged = True

                    pr.save()
                    logger.info(f"Linked PR #{pr_number} to contributor {github_username}")

            except Exception as e:
                logger.error(f"Error processing PR #{pr.issue_id}: {str(e)}")

        logger.info(f"Synced {len(all_contributors)} contributors for {repo.name}")

