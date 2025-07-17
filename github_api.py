import logging
import os
import random
from typing import Optional

import django
import requests
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blt.settings")
django.setup()

logger = logging.getLogger(__name__)


from website.views.aibot import get_github_aibot_token, get_github_aibot_username

MAX_RETRIES = 5
INITIAL_DELAY = 2
RETRY_HTTP_CODES = {500, 502, 503, 504, 429}

GITHUB_AIBOT_TOKEN = get_github_aibot_token()
GITHUB_AIBOT_USERNAME = get_github_aibot_username()


def _get_retry_wait_time(retry_state):
    """Custom wait function to respect GitHub's Retry-After header."""
    last_response = getattr(retry_state.outcome.exception(), "response", None)
    if last_response is not None and last_response.status_code == 429:
        retry_after = last_response.headers.get("Retry-After")
        if retry_after:
            return int(retry_after) + random.randint(1, 3)
    return wait_exponential_jitter(max=INITIAL_DELAY * 10)(retry_state)


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=_get_retry_wait_time,
    retry=(retry_if_exception_type((requests.exceptions.RequestException,))),
    before_sleep=before_sleep_log(logger, logging.INFO),
)
def fetch_pr_diff(pr_diff_url: str) -> Optional[str]:
    """
    Fetches PR diff using GitHub API with custom retry logic for error codes and rate limits.

    Args:
        pr_diff_url (str): URL to fetch the diff from

    Returns:
        str: Diff text if successful, None otherwise
    """
    headers = {
        "Authorization": f"Bearer {GITHUB_AIBOT_TOKEN}",
        "Accept": "application/vnd.github.v3.diff",
        "User-Agent": f"{GITHUB_AIBOT_USERNAME}/1.0",
    }

    logger.info("Fetching diff from: %s", pr_diff_url)

    response = requests.get(pr_diff_url, headers=headers, timeout=10)

    if response.status_code in RETRY_HTTP_CODES:
        logger.warning("Received retryable HTTP status code: %s", response.status_code)
        response.raise_for_status()

    if response.status_code == 200:
        return response.text

    return None
