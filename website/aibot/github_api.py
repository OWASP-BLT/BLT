import base64
import json
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import jwt
import requests
from django.conf import settings
from django.core.cache import caches
from tenacity import before_sleep_log, retry, retry_if_exception_type, stop_after_attempt, wait_exponential_jitter

logger = logging.getLogger(__name__)


MAX_RETRIES = 5
INITIAL_DELAY = 2
RETRY_HTTP_CODES = {500, 502, 503, 504, 429}


def _get_retry_wait_time(retry_state):
    """Custom wait function to respect GitHub's Retry-After header."""
    last_response = getattr(retry_state.outcome.exception(), "response", None)
    if last_response and last_response.status_code == 429:
        if retry_after := last_response.headers.get("Retry-After"):
            return int(retry_after) + random.randint(1, 3)
    return wait_exponential_jitter(max=INITIAL_DELAY * 10)(retry_state)


class GitHubTokenManager:
    def __init__(self, app_id: str, app_name: str, private_key: str):
        self.app_id = app_id
        self.app_name = app_name
        self.private_key = private_key.replace("\\n", "\n")
        try:
            self.cache = caches["redis"]
        except Exception as e:
            logger.warning("Unable to use 'redis' as cache: %s \n using default cache for GitHubTokenManager", e)
            self.cache = caches["default"]

    def _generate_jwt(self) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=9)).timestamp()),
            "iss": self.app_id,
        }
        token = jwt.encode(payload, self.private_key, algorithm="RS256")
        logger.debug("Generated new JWT for GitHub App authentication")
        return token

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=_get_retry_wait_time,
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        before_sleep=before_sleep_log(logger, logging.INFO),
    )
    def _fetch_installation_token(self, installation_id: int) -> tuple[str, datetime]:
        """Request a fresh installation token from GitHub."""
        jwt_token = self._generate_jwt()
        url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{settings.GITHUB_AIBOT_APP_NAME}/1.0",
        }
        logger.info("Requesting new installation token for ID %s via %s", installation_id, url)
        response = requests.post(url, headers=headers, timeout=5)

        if response.status_code in RETRY_HTTP_CODES:
            response.raise_for_status()
        elif response.status_code >= 400:
            logger.error("Failed to fetch installation token: %s %s", response.status_code, response.text)
            response.raise_for_status()

        data = response.json()

        expiry_str = data["expires_at"].replace("Z", "+00:00")
        expiry = datetime.fromisoformat(expiry_str)

        logger.debug(f"Fetched new token for installation {installation_id}, expires at {expiry.isoformat()}")
        return data["token"], expiry

    def get_token(self, installation_id: int) -> str:
        """Get cached or fresh token for this installation."""
        cache_key = f"github:token:{installation_id}"

        if cached_token := self.cache.get(cache_key):
            return cached_token

        token, expiry = self._fetch_installation_token(installation_id)
        ttl_seconds = int((expiry - datetime.now(timezone.utc)).total_seconds()) - 60

        if ttl_seconds > 0:
            logger.info(f"Cached token for installation {installation_id} with TTL {ttl_seconds}s")
            self.cache.set(cache_key, token, timeout=ttl_seconds)

        return token


class GitHubClient:
    """Lightweight client for GitHub API bound to one installation."""

    def __init__(
        self,
        installation_id: int,
        app_name: str,
        token_manager: GitHubTokenManager,
    ):
        self.installation_id = installation_id
        self.token_manager = token_manager
        self.base_url = "https://api.github.com"
        self.app_name = app_name

    def _headers(self):
        token = self.token_manager.get_token(self.installation_id)
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{self.app_name}/1.0",
        }

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=_get_retry_wait_time,
        retry=retry_if_exception_type(requests.exceptions.RequestException),
        before_sleep=before_sleep_log(logger, logging.INFO),
    )
    def _request(self, method: str, url: str, headers: Optional[Dict[str, str]] = None, **kwargs):
        """
        Perform an HTTP request with retries for transient errors and raise for all non-2xx responses.
        Logs errors with full response details for easier debugging.
        """
        final_headers = {**self._headers(), **(headers or {})}

        resp = requests.request(method, url, headers=final_headers, timeout=10, **kwargs)

        if resp.status_code in RETRY_HTTP_CODES:
            logger.warning(
                "Transient error from GitHub API: %s %s | Status: %s | Retrying...", method, url, resp.status_code
            )
            resp.raise_for_status()

        elif resp.status_code >= 400:
            logger.error("GitHub API request failed: %s %s | Status: %s", method, url, resp.status_code)
            logger.debug("GitHub API error response: %s", resp.text)
            resp.raise_for_status()

        else:
            logger.debug("GitHub API request succeeded: %s %s | Status: %s", method, url, resp.status_code)

        return resp

    def get(self, url: str, **kwargs):
        return self._request("GET", url, **kwargs)

    def post(self, url: str, **kwargs):
        return self._request("POST", url, **kwargs)

    def patch(self, url: str, **kwargs):
        return self._request("PATCH", url, **kwargs)

    def delete(self, url: str, **kwargs):
        return self._request("DELETE", url, **kwargs)

    def fetch_file_content(self, repo_full_name: str, path: str, ref: str) -> Optional[str]:
        url = f"{self.base_url}/repos/{repo_full_name}/contents/{path}?ref={ref}"
        logger.debug("Fetching file content via url: %s", url)
        try:
            response = self.get(url)
            data = response.json()
            logger.debug("Raw content response for %s: %s", path, json.dumps(data, indent=2))

            content = data.get("content")
            encoding = data.get("encoding")

            if not content:
                logger.warning("No content found for %s", path)
                return None

            if encoding == "base64":
                return base64.b64decode(content).decode("utf-8")
            elif encoding is None and isinstance(content, str):
                logger.warning("No encoding specified for %s, assuming plain text", path)
                return content
            else:
                logger.error("Unexpected encoding for %s: %s", path, encoding)
                return None

        except Exception as e:
            logger.error("Failed to fetch or decode file content for %s: %s", path, str(e))
            return None

    def fetch_pr_diff(self, pr_diff_url: str) -> Optional[str]:
        headers = {"Accept": "application/vnd.github.v3.diff"}
        try:
            response = self.get(pr_diff_url, headers=headers)
            return response.text
        except Exception as e:
            logger.error(
                "Failed to fetch PR diff. Installation: %s, URL: %s, Error: %s",
                self.installation_id,
                pr_diff_url,
                str(e),
            )
            return None

    def upsert_comment(
        self, comments_url: str, comment_body: str, comment_marker: Optional[str] = None
    ) -> Optional[tuple[requests.Response, str]]:
        try:
            target_comment_url = None

            if comment_marker:
                resp = self.get(comments_url)
                resp.raise_for_status()
                comments = resp.json()
                target_comment_url = next(
                    (c["url"] for c in comments if comment_marker in c.get("body", "")),
                    None,
                )

            if target_comment_url:
                return self.patch(target_comment_url, json={"body": comment_body}), "patched"
            else:
                return self.post(comments_url, json={"body": comment_body}), "posted"

        except Exception as e:
            logger.error(
                "Failed to upsert comment. Installation: %s, URL: %s, Marker: %s, Error: %s",
                self.installation_id,
                comments_url,
                comment_marker,
                str(e),
            )
            return None
