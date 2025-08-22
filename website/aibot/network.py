import base64
import logging
import random
import time
from typing import Any, Dict, List, Optional

import jwt
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
def get_github_installation_token(installation_id: str) -> str:
    """
    Generates a JWT and fetches a GitHub App installation token.
    """
    app_client_id = settings.GITHUB_AIBOT_APP_CLIENT_ID
    private_key = settings.GITHUB_AIBOT_PRIVATE_KEY.replace("\\n", "\n")

    now = int(time.time())
    payload = {
        "iat": now - 60,  # suggested in github docs
        "exp": now + (10 * 60),
        "iss": app_client_id,
    }
    jwt_token = jwt.encode(payload, private_key, algorithm="RS256")

    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{settings.GITHUB_AIBOT_APP_NAME}/1.0",
    }

    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    response = requests.post(url, headers=headers, timeout=5)

    if response.status_code in RETRY_HTTP_CODES:
        response.raise_for_status()
    if response.status_code == 201:
        return response.json()["token"]

    raise Exception(f"Failed to get installation token: {response.status_code} - {response.text}")


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=_get_retry_wait_time,
    retry=(retry_if_exception_type((requests.exceptions.RequestException,))),
    before_sleep=before_sleep_log(logger, logging.INFO),
)
def fetch_file_content(repo_full_name: str, path: str, ref: str, installation_token: str) -> Optional[str]:
    # NOTE: Initially implemented using raw.githubuser content, however it often takes time
    # to synchronize, leading to stale file content being fetched. The API is guaranteed to
    # be the latest (avoids CDN lag), thus more realiable
    url = f"https://api.github.com/repos/{repo_full_name}/contents/{path}?ref={ref}"
    headers = {
        "Authorization": f"Bearer {installation_token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": f"{settings.GITHUB_AIBOT_APP_NAME}/1.0",
    }

    response = requests.get(url, headers=headers, timeout=5)
    if response.status_code in RETRY_HTTP_CODES:
        response.raise_for_status()
    if response.status_code != 200:
        logger.warning("GitHub API failed for %s: %s", path, response.text)
        return None

    data = response.json()
    if data.get("encoding") != "base64":
        logger.error("Unexpected encoding for file %s", path)
        return None

    try:
        return base64.b64decode(data["content"]).decode("utf-8")
    except Exception as e:
        logger.error("Failed to decode content for %s: %s", path, str(e))
        return None


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=_get_retry_wait_time,
    retry=(retry_if_exception_type((requests.exceptions.RequestException,))),
    before_sleep=before_sleep_log(logger, logging.INFO),
)
def github_api_get(api_url: str, installation_token: str) -> Optional[str]:
    headers = {
        "Authorization": f"Bearer {installation_token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": f"{settings.GITHUB_AIBOT_APP_NAME}/1.0",
    }

    response = requests.get(api_url, headers=headers, timeout=5)
    if response.status_code in RETRY_HTTP_CODES:
        response.raise_for_status()
    if response.status_code == 200:
        return response.json()

    return None


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=_get_retry_wait_time,
    retry=(retry_if_exception_type((requests.exceptions.RequestException,))),
    before_sleep=before_sleep_log(logger, logging.INFO),
)
def fetch_pr_diff(pr_diff_url: str, installation_token: str) -> Optional[str]:
    """
    Fetches the raw diff for a pull request using the GitHub App installation token.
    Returns the diff as a string, or None if the request fails.
    """
    headers = {
        "Authorization": f"Bearer {installation_token}",
        "Accept": "application/vnd.github.v3.diff",
        "User-Agent": f"{settings.GITHUB_AIBOT_APP_NAME}/1.0",
    }

    response = requests.get(pr_diff_url, headers=headers, timeout=5)
    if response.status_code in RETRY_HTTP_CODES:
        response.raise_for_status()
    if response.status_code == 200:
        return response.text

    logger.warning(
        "Failed to fetch PR diff from %s. Status code: %s. Response: %s",
        pr_diff_url,
        response.status_code,
        response.text,
    )


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=_get_retry_wait_time,
    retry=(retry_if_exception_type((requests.exceptions.RequestException,))),
    before_sleep=before_sleep_log(logger, logging.INFO),
)
def post_github_comment(comments_url: str, comment_body: str, installation_token: str) -> Optional[str]:
    headers = {
        "Authorization": f"Bearer {installation_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{settings.GITHUB_AIBOT_APP_NAME}/1.0",
    }

    payload = {"body": comment_body}

    response = requests.post(comments_url, headers=headers, json=payload, timeout=5)
    if response.status_code in RETRY_HTTP_CODES:
        response.raise_for_status()
    if response.status_code == 201:
        return response.json()
    return None


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=_get_retry_wait_time,
    retry=(retry_if_exception_type((requests.exceptions.RequestException,))),
    before_sleep=before_sleep_log(logger, logging.INFO),
)
def patch_github_comment(
    comments_url: str, comment_body: str, comment_marker: str, installation_token: str
) -> Optional[str]:
    headers = {
        "Authorization": f"Bearer {installation_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{settings.GITHUB_AIBOT_APP_NAME}/1.0",
    }

    response = requests.get(comments_url, headers=headers, timeout=5)
    if response.status_code != 200:
        response.raise_for_status()
    comments = response.json()

    target_comment_id = None
    for comment in comments:
        if comment_marker in comment.get("body", ""):
            target_comment_id = comment["id"]
            break

    if not target_comment_id:
        logger.warning("No existing comment found with marker: %s", comment_marker)
        return None

    patch_url = f"{comments_url}/{target_comment_id}"
    patch_payload = {"body": comment_body}
    patch_response = requests.patch(patch_url, headers=headers, json=patch_payload, timeout=5)

    if patch_response.status_code in RETRY_HTTP_CODES:
        patch_response.raise_for_status()
    if patch_response.status_code == 200:
        return patch_response.json()

    logger.warning("Failed to patch comment: %s", comments_url)
    return None


def generate_gemini_response(prompt: str) -> Optional[Dict[str, Any]]:
    """
    Generates a response from the Gemini model for the given prompt.
    Returns structured data including text, model info, and token usage.
    """

    if not prompt or not isinstance(prompt, str):
        raise ValueError(f"Invalid prompt provided: {prompt}. Prompt must be a non-empty string.")

    try:
        response = gemini_model.generate_content(prompt)

        if response and response.text:
            return {
                "text": response.text,
                "model": getattr(response, "model", "gemini-2.0-flash"),
                "prompt_tokens": getattr(response, "usage", {}).get("prompt_tokens", 0),
                "completion_tokens": getattr(response, "usage", {}).get("completion_tokens", 0),
            }

        logger.warning(
            "Gemini model returned an empty or non-text response for prompt: '%s'. Response: %s", prompt, response
        )
        return None

    except Exception as e:
        logger.error("Gemini API error for prompt '%s': %s", prompt, e)
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
