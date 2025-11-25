"""
CVE caching utilities for NVD API responses.
"""

import logging
import time
from decimal import Decimal

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Default cache timeout: 24 hours (86400 seconds)
# CVE data doesn't change frequently, so long cache is appropriate
CVE_CACHE_TIMEOUT = getattr(settings, "CVE_CACHE_TIMEOUT", 86400)

# API timeout: 10 seconds (consistent with other API calls in codebase)
CVE_API_TIMEOUT = getattr(settings, "CVE_API_TIMEOUT", 10)

# Max attempts for API retries (used for 429 handling)
CVE_API_MAX_RETRIES = getattr(settings, "CVE_API_MAX_RETRIES", 3)

# Base delay (seconds) for exponential backoff when rate limited
CVE_RATE_LIMIT_BACKOFF_BASE = getattr(settings, "CVE_RATE_LIMIT_BACKOFF_BASE", 0.5)

# Cache key prefix
CVE_CACHE_KEY_PREFIX = "cve"

# Sentinel value to cache None results (distinguish from cache miss)
CACHE_NONE = "<CACHED_NONE>"

# Cache lock settings to avoid duplicate API calls
CVE_CACHE_LOCK_SUFFIX = ":lock"
CVE_CACHE_LOCK_TIMEOUT = getattr(settings, "CVE_CACHE_LOCK_TIMEOUT", 30)
CVE_CACHE_LOCK_WAIT_TIMEOUT = getattr(settings, "CVE_CACHE_LOCK_WAIT_TIMEOUT", 5)
CVE_CACHE_LOCK_WAIT_INTERVAL = getattr(
    settings, "CVE_CACHE_LOCK_WAIT_INTERVAL", 0.2
)


def normalize_cve_id(cve_id):
    """Normalize CVE ID casing/whitespace to avoid duplicate cache keys."""
    if not cve_id:
        return ""
    return cve_id.strip().upper()


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
        logger.debug("Cache fill wait timed out for %s, continuing", normalized_id)

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

    while attempt < CVE_API_MAX_RETRIES:
        try:
            url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}"
            response = requests.get(url, timeout=CVE_API_TIMEOUT)
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
            if status_code == 429 and attempt < CVE_API_MAX_RETRIES - 1:
                wait_seconds = CVE_RATE_LIMIT_BACKOFF_BASE * (2**attempt)
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
        cache.set(cache_key, cache_value, timeout=CVE_CACHE_TIMEOUT)
        logger.debug("Cached CVE score for %s", cve_id)
    except Exception as e:  # noqa: BLE001  # pylint: disable=broad-except
        logger.warning("Error caching CVE score for %s: %s", cve_id, e)


def _acquire_cache_lock(lock_key):
    """Attempt to acquire cache-backed lock."""
    try:
        return cache.add(lock_key, True, timeout=CVE_CACHE_LOCK_TIMEOUT)
    except Exception as e:  # noqa: BLE001  # pylint: disable=broad-except
        logger.warning("Error acquiring cache lock %s: %s", lock_key, e)
        return False


def _wait_for_cache_fill(cache_key, cve_id):
    """Wait briefly for another worker to populate the cache."""
    deadline = time.monotonic() + CVE_CACHE_LOCK_WAIT_TIMEOUT
    while time.monotonic() < deadline:
        cached_value, is_hit = _read_from_cache(cache_key, cve_id)
        if is_hit:
            return cached_value, True
        time.sleep(CVE_CACHE_LOCK_WAIT_INTERVAL)
    return None, False
