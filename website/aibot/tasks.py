import logging
from typing import Dict, List

from celery import shared_task

from website.aibot.github_api import GitHubClient
from website.aibot.qdrant_api import q_process_repository
from website.models import GithubAppInstallation

logger = logging.getLogger(__name__)


@shared_task
def process_repos_added_task(repositories: List[Dict], installation: GithubAppInstallation, gh_client: GitHubClient):
    processed_repos, failed_repos = [], []
    for repo in repositories:
        success, failed = q_process_repository(repo, installation, gh_client)
        if success:
            processed_repos.append(success)
        if failed:
            failed_repos.append(failed)

    logger.info(
        "Repository processing completed: %d succeeded, %d failed. Successful: %s | Failed: %s",
        len(processed_repos),
        len(failed_repos),
        [r.name for r in processed_repos],
        [r.name for r in failed_repos],
    )


@shared_task
def process_repos_removed_task(repositories: List[Dict], installation: GithubAppInstallation, gh_client: GitHubClient):
    processed_repos, failed_repos = [], []
    for repo in repositories:
        success, failed = q_process_repository(repo, installation, gh_client)
        if success:
            processed_repos.append(success)
        if failed:
            failed_repos.append(failed)

    logger.info(
        "Repository processing completed: %d succeeded, %d failed. Successful: %s | Failed: %s",
        len(processed_repos),
        len(failed_repos),
        [r.name for r in processed_repos],
        [r.name for r in failed_repos],
    )
