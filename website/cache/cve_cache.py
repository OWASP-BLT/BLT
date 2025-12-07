"""
CVE caching utilities for NVD API responses.
"""

import logging
import re
import time
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
        logger.warning("Invalid CVE ID format: %s", cve_id)
        return ""
    return normalized


def get_cve_cache_key(cve_id):
    """Generate cache key for CVE data."""
    normalized_id = normalize_cve_id(cve_id)
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

    cache_key = get_cve_cache_key(normalized_id)

    cached_value, is_hit = _read_from_cache(cache_key, normalized_id)
    if is_hit:
        return cached_value

    lock_key = f"{cache_key}{CVE_CACHE_LOCK_SUFFIX}"
    lock_acquired = _acquire_cache_lock(lock_key)

    if not lock_acquired:
        logger.debug("Waiting for existing fetch lock for %s", normalized_id)
        cached_value, is_hit = _wait_for_cache_fill(cache_key, normalized_id)
        if is_hit:
            return cached_value
        logger.debug("Cache fill wait timed out for %s, retrying lock acquisition", normalized_id)
        # Try to acquire lock one more time after timeout
        lock_acquired = _acquire_cache_lock(lock_key)
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
        score = fetch_cve_score_from_api(normalized_id)
        _write_to_cache(cache_key, normalized_id, score)
        return score
    finally:
        if lock_acquired:
            cache.delete(lock_key)


def fetch_cve_score_from_api(cve_id):
    """
    Fetch CVE score directly from NVD API.

    Args:
        cve_id: CVE identifier (e.g., "CVE-2024-1234")

    Returns:
        Decimal score if found, None otherwise
    """
    normalized_id = normalize_cve_id(cve_id)
    if not normalized_id:
        return None

    cve_id = normalized_id
    attempt = 0
    max_retries = _get_max_retries()
    api_timeout = _get_api_timeout()

    while attempt < max_retries:
        try:
            # URL encode CVE ID to prevent injection attacks
            encoded_cve_id = quote(cve_id, safe="")
            url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={encoded_cve_id}"
            response = requests.get(url, timeout=api_timeout)
            response.raise_for_status()

            data = response.json()
            results = data.get("resultsPerPage", 0)

            if results == 0:
                logger.debug("No results found for CVE %s", cve_id)
                return None

            vulnerabilities = data.get("vulnerabilities", [])
            if not vulnerabilities:
                return None

            metrics = vulnerabilities[0].get("cve", {}).get("metrics", {})
            if not metrics:
                return None

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
                return None

            base_score = cvss_data[0].get("cvssData", {}).get("baseScore")

            if base_score is not None:
                return Decimal(str(base_score))

            return None

        except requests.exceptions.Timeout:
            logger.warning("Timeout fetching CVE score for %s", cve_id)
            return None
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response else None
            if status_code == 429 and attempt < max_retries - 1:
                wait_seconds = _get_backoff_base() * (2**attempt)
                logger.warning(
                    "Rate limit exceeded when fetching CVE score for %s; retrying in %.2fs",
                    cve_id,
                    wait_seconds,
                )
                time.sleep(wait_seconds)
                attempt += 1
                continue
            if status_code == 429:
                logger.warning(
                    "Rate limit exceeded when fetching CVE score for %s",
                    cve_id,
                )
            else:
                logger.warning(
                    "HTTP error fetching CVE score for %s: %s",
                    cve_id,
                    e,
                )
            return None
        except requests.exceptions.ConnectionError as e:
            logger.warning(
                "Connection error fetching CVE score for %s: %s",
                cve_id,
                e,
            )
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(
                "Request error fetching CVE score for %s: %s",
                cve_id,
                e,
            )
            return None
        except (KeyError, IndexError, ValueError) as e:
            logger.warning("Error parsing CVE response for %s: %s", cve_id, e)
            return None
        except Exception as e:  # noqa: BLE001  # pylint: disable=broad-except
            logger.warning(
                "Unexpected error fetching CVE score for %s: %s",
                cve_id,
                e,
            )
            return None

    return None


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
    """Attempt to acquire cache-backed lock."""
    try:
        return cache.add(lock_key, True, timeout=_get_lock_timeout())
    except Exception as e:  # noqa: BLE001  # pylint: disable=broad-except
        logger.warning("Error acquiring cache lock %s: %s", lock_key, e)
        return False


def _wait_for_cache_fill(cache_key, cve_id):
    """
    Wait briefly for another worker to populate the cache.

    Returns immediately if cache is populated, otherwise waits up to
    the configured wait timeout seconds with short intervals to avoid
    blocking the worker thread for extended periods.
    """
    wait_timeout = _get_lock_wait_timeout()
    wait_interval = _get_lock_wait_interval()
    deadline = time.monotonic() + wait_timeout
    iterations = 0
    max_iterations = int(wait_timeout / wait_interval)

    while iterations < max_iterations:
        cached_value, is_hit = _read_from_cache(cache_key, cve_id)
        if is_hit:
            return cached_value, True
        # Only sleep if we're not at the deadline
        if time.monotonic() < deadline:
            time.sleep(wait_interval)
            iterations += 1
        else:
            break
    return None, False
