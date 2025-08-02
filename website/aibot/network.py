import logging
import random
from typing import List, Optional

import requests
from django.conf import settings
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

from website.aibot.clients import gemini_model, genai

logger = logging.getLogger(__name__)

MAX_RETRIES = 5
INITIAL_DELAY = 2
RETRY_HTTP_CODES = {500, 502, 503, 504, 429}

# Retry based on criticality and dependency


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
        "Authorization": f"Bearer {settings.GITHUB_AIBOT_TOKEN}",
        "Accept": "application/vnd.github.v3.diff",
        "User-Agent": f"{settings.GITHUB_AIBOT_USERNAME}/1.0",
    }

    response = requests.get(pr_diff_url, headers=headers, timeout=5)
    if response.status_code in RETRY_HTTP_CODES:
        response.raise_for_status()
    if response.status_code == 200:
        return response.text

    return None


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=_get_retry_wait_time,
    retry=(retry_if_exception_type((requests.exceptions.RequestException,))),
    before_sleep=before_sleep_log(logger, logging.INFO),
)
def fetch_pr_files(pr_files_url: str) -> Optional[str]:
    headers = {
        "Authorization": f"Bearer {settings.GITHUB_AIBOT_TOKEN}",
        "Accept": "application/vnd.github.v3",
        "User-Agent": f"{settings.GITHUB_AIBOT_USERNAME}/1.0",
    }

    response = requests.get(pr_files_url, headers=headers, timeout=5)
    if response.status_code in RETRY_HTTP_CODES:
        response.raise_for_status()
    if response.status_code == 200:
        return response.text

    return None


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=_get_retry_wait_time,
    retry=(retry_if_exception_type((requests.exceptions.RequestException,))),
    before_sleep=before_sleep_log(logger, logging.INFO),
)
def fetch_raw_content(f_raw_url: str) -> Optional[str]:
    headers = {
        "Authorization": f"Bearer {settings.GITHUB_AIBOT_TOKEN}",
        "Accept": "application/vnd.github.v3",
        "User-Agent": f"{settings.GITHUB_AIBOT_USERNAME}/1.0",
    }

    response = requests.get(f_raw_url, headers=headers, timeout=5)
    if response.status_code in RETRY_HTTP_CODES:
        response.raise_for_status()
    if response.status_code == 200:
        return response.text

    return None


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=_get_retry_wait_time,
    retry=(retry_if_exception_type((requests.exceptions.RequestException,))),
    before_sleep=before_sleep_log(logger, logging.INFO),
)
def post_github_comment(comments_url: str, comment_body: str) -> Optional[str]:
    headers = {
        "Authorization": f"Bearer {settings.GITHUB_AIBOT_TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{settings.GITHUB_AIBOT_USERNAME}/1.0",
    }

    payload = {"body": comment_body}

    response = requests.post(comments_url, headers=headers, json=payload, timeout=5)
    if response.status_code in RETRY_HTTP_CODES:
        response.raise_for_status()
    if response.status_code == 201:
        return response.text
    return None


def generate_gemini_response(prompt: str) -> Optional[str]:
    """
    Generates a response from the Gemini model for the given prompt.
    Handles internal errors by returning None and logging the issue.

    Args:
        prompt: The input string prompt for the Gemini model.

    Returns:
        The generated text response as a string, or None if:
        - The prompt is invalid (not a non-empty string).
        - An error occurs during the Gemini API call.
        - The Gemini model returns an empty response.
    """
    if not prompt or not isinstance(prompt, str):
        raise ValueError(f"Invalid prompt provided: {prompt}. Prompt must be a non-empty string.")

    try:
        response = gemini_model.generate_content(prompt)
        if response and response.text:
            return response.text
        else:
            logger.warning(
                f"Gemini model returned an empty or non-text response for prompt: '{prompt}'. Response: {response}"
            )
            return None

    except Exception as e:
        logger.error(f"An error occurred during Gemini API call for prompt '{prompt}': {e}")
        return None


def generate_embedding(
    text: str, title: str = None, embedding_model=settings.GEMINI_EMBEDDING_MODEL
) -> Optional[List[float]]:
    """
    Generates an embedding from the given text using the Gemini model.

    Args:
        text (str): The input text.
        title (str, optional): Title of the content. Defaults to "Untitled".
        embedding_model (str): The Gemini embedding model to use.

    Returns:
        Optional[List[float]]: The embedding vector, or None if an error occurs.
    """
    try:
        response = genai.embed_content(
            model=embedding_model,
            content=text,
            task_type="retrieval_document",
            title=title or "Untitled",
        )
        return response.get("embedding")
    except Exception as e:
        logger.error(f"Embedding generation failed for text: {text} - {e}")
        return None
