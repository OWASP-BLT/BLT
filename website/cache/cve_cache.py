"""
CVE caching utilities for NVD API responses.
"""

import decimal
import logging
import re
import time
import uuid
from decimal import Decimal
from urllib.parse import quote

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# CVE ID format validation pattern: CVE-YYYY-NNNN (4-7 digits)
CVE_ID_PATTERN = re.compile(r"^CVE-\d{4}-\d{4,7}$")

# Cache key prefix
CVE_CACHE_KEY_PREFIX = "cve"

# Sentinel value to cache None results (distinguish from cache miss)
CACHE_NONE = "<CACHED_NONE>"

# Cache lock settings
CVE_CACHE_LOCK_SUFFIX = ":lock"


def _get_cache_timeout():
    """Get cache timeout from settings (lazy)."""
    return getattr(settings, "CVE_CACHE_TIMEOUT", 86400)


def _get_api_timeout():
    """Get API timeout from settings (lazy)."""
    return getattr(settings, "CVE_API_TIMEOUT", 10)


def _get_max_retries():
    """Get max retries from settings (lazy)."""
    return getattr(settings, "CVE_API_MAX_RETRIES", 3)


def _get_backoff_base():
    """Get backoff base from settings (lazy)."""
    return getattr(settings, "CVE_RATE_LIMIT_BACKOFF_BASE", 0.5)


def _get_lock_timeout():
    """Get lock timeout from settings (lazy)."""
    return getattr(settings, "CVE_CACHE_LOCK_TIMEOUT", 30)


def _get_lock_wait_timeout():
    """Get lock wait timeout from settings (lazy)."""
    return getattr(settings, "CVE_CACHE_LOCK_WAIT_TIMEOUT", 5)


def _get_lock_wait_interval():
    """Get lock wait interval from settings (lazy)."""
    return getattr(settings, "CVE_CACHE_LOCK_WAIT_INTERVAL", 0.2)


def normalize_cve_id(cve_id):
    """Normalize and validate CVE ID format."""
    if not cve_id:
        return ""
    normalized = cve_id.strip().upper()
    if not CVE_ID_PATTERN.match(normalized):
        # Log at debug level with sanitized input to prevent log injection
        # Use repr() to escape newlines and other control characters
        logger.debug("Invalid CVE ID format: %s", repr(cve_id[:100]))  # Limit length to prevent log flooding
        return ""
    return normalized


def get_cve_cache_key(cve_id):
    """
    Generate cache key for CVE data.

    Args:
        cve_id: CVE identifier (e.g., "CVE-2024-1234")

    Returns:
        str: Cache key in format "cve:{normalized_id}"

    Raises:
        ValueError: If cve_id is invalid or normalized_id is empty
    """
    normalized_id = normalize_cve_id(cve_id)
    if not normalized_id:
        raise ValueError(f"Invalid CVE ID format: {cve_id}. Expected format: CVE-YYYY-NNNN")
    return f"{CVE_CACHE_KEY_PREFIX}:{normalized_id}"


def get_cached_cve_score(cve_id):
    """
    Get CVE score from cache or fetch from NVD API.

    Args:
        cve_id: CVE identifier (e.g., "CVE-2024-1234")

    Returns:
        Decimal score if found, None otherwise
    """
    normalized_id = normalize_cve_id(cve_id)
    if not normalized_id:
        return None

    # Defensive: handle potential ValueError from get_cve_cache_key
    # (shouldn't happen since normalized_id is validated, but be safe)
    try:
        cache_key = get_cve_cache_key(normalized_id)
    except ValueError:
        # Invalid CVE ID format - return None without caching
        logger.warning("Invalid CVE ID format in get_cached_cve_score: %s", normalized_id)
        return None

    cached_value, is_hit = _read_from_cache(cache_key, normalized_id)
    if is_hit:
        return cached_value

    lock_key = f"{cache_key}{CVE_CACHE_LOCK_SUFFIX}"
    lock_token = None  # Track our lock token for safe release
    lock_acquired, lock_token = _acquire_cache_lock(lock_key)

    if not lock_acquired:
        logger.debug("Waiting for existing fetch lock for %s", normalized_id)
        cached_value, is_hit = _wait_for_cache_fill(cache_key, normalized_id)
        if is_hit:
            return cached_value
        logger.debug("Cache fill wait timed out for %s, retrying lock acquisition", normalized_id)
        # Try to acquire lock one more time after timeout
        lock_acquired, lock_token = _acquire_cache_lock(lock_key)
        if not lock_acquired:
            # Still can't acquire lock - check cache one final time before proceeding
            cached_value, is_hit = _read_from_cache(cache_key, normalized_id)
            if is_hit:
                return cached_value
            logger.warning(
                "Proceeding without lock for %s - multiple concurrent requests may cause duplicate API calls",
                normalized_id,
            )

    try:
        # Check cache again to avoid duplicate API calls after acquiring lock
        cached_value, is_hit = _read_from_cache(cache_key, normalized_id)
        if is_hit:
            return cached_value

        logger.debug("CVE score cache miss for %s, fetching from API", normalized_id)
        score, had_error = fetch_cve_score_from_api(normalized_id)
        # Only cache successful responses (score or None for "not found")
        # Do NOT cache API errors (5xx, network failures) to avoid stale error states
        if not had_error:
            _write_to_cache(cache_key, normalized_id, score)
        return score
    finally:
        if lock_acquired and lock_token:
            # Only release the lock if it's still ours (tokenized lock prevents stomping)
            try:
                _release_cache_lock(lock_key, lock_token)
            except Exception as e:  # noqa: BLE001  # pylint: disable=broad-except
                logger.warning("Error releasing cache lock %s: %s", lock_key, e)


def fetch_cve_score_from_api(cve_id):
    """
    Fetch CVE score directly from NVD API.

    Args:
        cve_id: CVE identifier (e.g., "CVE-2024-1234")

    Returns:
        tuple: (Decimal score if found else None, had_error: bool)
        had_error=True means API error occurred (don't cache), False means valid response (can cache)
    """
    normalized_id = normalize_cve_id(cve_id)
    if not normalized_id:
        return None, False  # Valid: invalid CVE format (can cache as "not found")

    cve_id = normalized_id
    attempt = 0
    max_retries = _get_max_retries()
    api_timeout = _get_api_timeout()

    while attempt < max_retries:
        try:
            # URL encode CVE ID to prevent injection attacks
            encoded_cve_id = quote(cve_id, safe="")
            url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={encoded_cve_id}"

            # NVD-recommended headers
            headers = {"User-Agent": "BLT-CVE-Checker/1.0 (https://github.com/OWASP-BLT/BLT; contact@owasp.org)"}

            # Add API key if configured (case-sensitive header per NVD spec)
            api_key = getattr(settings, "NVD_API_KEY", None)
            if api_key:
                headers["apiKey"] = api_key

            response = requests.get(url, headers=headers, timeout=api_timeout)
            response.raise_for_status()

            data = response.json()
            # Use totalResults (NVD API 2.0 spec), fallback to resultsPerPage for older API versions
            total_results = data.get("totalResults", data.get("resultsPerPage", 0))

            if total_results == 0:
                logger.debug("No results found for CVE %s", cve_id)
                return None, False  # Valid response: CVE not found (can cache)

            vulnerabilities = data.get("vulnerabilities", [])
            if not vulnerabilities:
                return None, False  # Valid response: no vulnerabilities (can cache)

            metrics = vulnerabilities[0].get("cve", {}).get("metrics", {})
            if not metrics:
                return None, False  # Valid response: no metrics (can cache)

            # Prefer CVSS v3.1, then v3.0, then v2.0
            preferred_versions = ["cvssMetricV31", "cvssMetricV30", "cvssMetricV2"]
            cvss_metric_v = None
            cvss_data = None

            for version_key in preferred_versions:
                if version_key in metrics:
                    candidate_data = metrics[version_key]
                    if candidate_data and len(candidate_data) > 0:
                        cvss_metric_v = version_key
                        cvss_data = candidate_data
                        break

            if not cvss_metric_v or not cvss_data:
                return None, False  # Valid response: no CVSS data (can cache)

            base_score = cvss_data[0].get("cvssData", {}).get("baseScore")

            if base_score is not None:
                try:
                    # Convert to Decimal - can raise ValueError for invalid formats
                    score = Decimal(str(base_score))
                    return score, False  # Valid response: score found (can cache)
                except (ValueError, TypeError, decimal.InvalidOperation) as e:
                    # Malformed score value that can't be converted to Decimal
                    logger.error("Invalid score format for CVE %s: %s", cve_id, e)
                    return None, True  # Error: malformed data (don't cache)

            return None, False  # Valid response: score is None (can cache)

        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                wait_seconds = _get_backoff_base() * (2**attempt)
                logger.warning(
                    "Timeout fetching CVE score for %s; retrying in %.2fs",
                    cve_id,
                    wait_seconds,
                )
                time.sleep(wait_seconds)
                attempt += 1
                continue
            logger.warning("Timeout fetching CVE score for %s after %d attempts", cve_id, max_retries)
            return None, True  # Error: timeout (don't cache)
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            # Retry on 429 (rate limit) and 5xx (server errors) with exponential backoff
            if status_code in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                wait_seconds = _get_backoff_base() * (2**attempt)
                if status_code == 429:
                    # Check Retry-After header for rate limits
                    retry_after = e.response.headers.get("Retry-After") if e.response else None
                    if retry_after:
                        try:
                            wait_seconds = float(retry_after)
                        except (ValueError, TypeError):
                            pass
                logger.warning(
                    "HTTP %s error fetching CVE score for %s; retrying in %.2fs",
                    status_code,
                    cve_id,
                    wait_seconds,
                )
                time.sleep(wait_seconds)
                attempt += 1
                continue
            if status_code == 429:
                logger.warning(
                    "Rate limit exceeded when fetching CVE score for %s after %d attempts",
                    cve_id,
                    max_retries,
                )
            elif status_code is not None and 500 <= status_code < 600:
                logger.error(
                    "Server error %s fetching CVE score for %s after %d attempts",
                    status_code,
                    cve_id,
                    max_retries,
                )
            else:
                logger.warning(
                    "HTTP error %s fetching CVE score for %s: %s",
                    status_code,
                    cve_id,
                    e,
                )
            return None, True  # Error: HTTP error (don't cache)
        except requests.exceptions.ConnectionError as e:
            # Treat ConnectionError as retriable (transient network issues)
            if attempt < max_retries - 1:
                wait_seconds = _get_backoff_base() * (2**attempt)
                logger.warning(
                    "Connection error fetching CVE score for %s; retrying in %.2fs (attempt %d/%d)",
                    cve_id,
                    wait_seconds,
                    attempt + 1,
                    max_retries,
                )
                time.sleep(wait_seconds)
                attempt += 1
                continue
            logger.warning(
                "Connection error fetching CVE score for %s after %d attempts: %s",
                cve_id,
                max_retries,
                e,
            )
            return None, True  # Error: connection failed after retries (don't cache)
        except requests.exceptions.RequestException as e:
            logger.warning(
                "Request error fetching CVE score for %s: %s",
                cve_id,
                e,
            )
            return None, True  # Error: request exception (don't cache)
        except (KeyError, IndexError, ValueError) as e:
            logger.warning("Error parsing CVE response for %s: %s", cve_id, e)
            return None, True  # Error: malformed response (don't cache)
        except Exception as e:  # noqa: BLE001  # pylint: disable=broad-except
            logger.warning(
                "Unexpected error fetching CVE score for %s: %s",
                cve_id,
                e,
            )
            return None, True  # Error: unexpected exception (don't cache)

    return None, True  # Error: max retries exceeded (don't cache)


def _read_from_cache(cache_key, cve_id):
    """Read cache entry, handling sentinel."""
    try:
        cached_value = cache.get(cache_key)
    except Exception as e:  # noqa: BLE001  # pylint: disable=broad-except
        logger.warning("Error reading from cache for %s: %s", cve_id, e)
        return None, False

    if cached_value is None:
        return None, False

    logger.debug("CVE score cache hit for %s", cve_id)
    if cached_value == CACHE_NONE:
        return None, True
    return cached_value, True


def _write_to_cache(cache_key, cve_id, score):
    """Persist score (including None) using sentinel value."""
    try:
        cache_value = CACHE_NONE if score is None else score
        cache.set(cache_key, cache_value, timeout=_get_cache_timeout())
        logger.debug("Cached CVE score for %s", cve_id)
    except Exception as e:  # noqa: BLE001  # pylint: disable=broad-except
        logger.warning("Error caching CVE score for %s: %s", cve_id, e)


def _acquire_cache_lock(lock_key):
    """
    Attempt to acquire cache-backed lock with unique token.

    Returns:
        tuple: (acquired: bool, token: str or None)
        - acquired=True means we got the lock
        - token is our unique identifier for safe release
    """
    try:
        # Generate unique token for this lock acquisition
        lock_token = str(uuid.uuid4())
        acquired = cache.add(lock_key, lock_token, timeout=_get_lock_timeout())
        if acquired:
            return True, lock_token
        return False, None
    except Exception as e:  # noqa: BLE001  # pylint: disable=broad-except
        logger.warning("Error acquiring cache lock %s: %s", lock_key, e)
        return False, None


def _release_cache_lock(lock_key, expected_token):
    """
    Release cache-backed lock only if it still contains our token.
    This prevents releasing another worker's lock if ours expired.
    """
    try:
        current_value = cache.get(lock_key)
        if current_value == expected_token:
            cache.delete(lock_key)
            logger.debug("Successfully released lock %s", lock_key)
        else:
            logger.debug(
                "Lock %s already expired or taken by another worker (our token: %s, current: %s)",
                lock_key,
                expected_token,
                current_value,
            )
    except Exception as e:  # noqa: BLE001  # pylint: disable=broad-except
        logger.warning("Error checking/releasing cache lock %s: %s", lock_key, e)


def _wait_for_cache_fill(cache_key, cve_id):
    """
    Wait briefly for another worker to populate the cache.
    Returns immediately if cache is populated, otherwise waits up to
    the configured wait timeout seconds with short intervals to avoid
    blocking the worker thread for extended periods.
    """
    wait_timeout = _get_lock_wait_timeout()
    wait_interval = _get_lock_wait_interval()
    # Normalize misconfigured interval: must be positive
    if wait_interval <= 0:
        # Fallback to a small sane default, capped by timeout if needed
        if wait_timeout > 0:
            wait_interval = min(wait_timeout, 0.2)
        else:
            wait_interval = 0.2
    deadline = time.monotonic() + wait_timeout
    iterations = 0
    # Ensure at least one iteration even if interval > timeout
    max_iterations = max(1, int(wait_timeout / wait_interval))
    while iterations < max_iterations:
        cached_value, is_hit = _read_from_cache(cache_key, cve_id)
        if is_hit:
            return cached_value, True
        # Only sleep if we're not yet past the deadline
        if time.monotonic() < deadline:
            time.sleep(wait_interval)
        iterations += 1
    # Timed out waiting for another worker to fill cache
    return None, False
