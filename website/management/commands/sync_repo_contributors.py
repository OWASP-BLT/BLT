import logging
import time

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from website.models import Contributor, Repo

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

        repo.contributor_count = len(all_contributors)
        repo.save()

        logger.info(f"Synced {len(all_contributors)} contributors for {repo.name}")
