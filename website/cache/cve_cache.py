"""
CVE caching utilities for NVD API responses.
"""
import logging
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

# Cache key prefix
CVE_CACHE_KEY_PREFIX = "cve"


def get_cve_cache_key(cve_id):
    """Generate cache key for CVE data."""
    return f"{CVE_CACHE_KEY_PREFIX}:{cve_id}"


def get_cached_cve_score(cve_id):
    """
    Get CVE score from cache or fetch from NVD API.
    
    Args:
        cve_id: CVE identifier (e.g., "CVE-2024-1234")
        
    Returns:
        Decimal score if found, None otherwise
    """
    if not cve_id:
        return None
    
    cache_key = get_cve_cache_key(cve_id)
    
    # Try to get from cache first
    try:
        cached_score = cache.get(cache_key)
        if cached_score is not None:
            logger.debug(f"CVE score cache hit for {cve_id}")
            return cached_score
    except Exception as e:
        logger.warning(f"Error reading from cache for {cve_id}: {e}")
        # Continue to API call on cache error
    
    # Cache miss - fetch from API
    logger.debug(f"CVE score cache miss for {cve_id}, fetching from API")
    score = fetch_cve_score_from_api(cve_id)
    
    # Cache the result (even if None, to avoid repeated API calls for invalid CVEs)
    if score is not None:
        try:
            cache.set(cache_key, score, timeout=CVE_CACHE_TIMEOUT)
            logger.debug(f"Cached CVE score for {cve_id}")
        except Exception as e:
            logger.warning(f"Error caching CVE score for {cve_id}: {e}")
            # Continue even if caching fails
    
    return score


def fetch_cve_score_from_api(cve_id):
    """
    Fetch CVE score directly from NVD API.
    
    Args:
        cve_id: CVE identifier (e.g., "CVE-2024-1234")
        
    Returns:
        Decimal score if found, None otherwise
    """
    if not cve_id:
        return None
    
    try:
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id}"
        response = requests.get(url, timeout=CVE_API_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        results = data.get("resultsPerPage", 0)
        
        if results == 0:
            logger.debug(f"No results found for CVE {cve_id}")
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
        logger.warning(f"Timeout fetching CVE score for {cve_id}")
        return None
    except requests.exceptions.HTTPError as e:
        # Handle rate limiting (429) and other HTTP errors
        if e.response and e.response.status_code == 429:
            logger.warning(f"Rate limit exceeded when fetching CVE score for {cve_id}")
        else:
            logger.warning(f"HTTP error fetching CVE score for {cve_id}: {e}")
        return None
    except requests.exceptions.ConnectionError as e:
        logger.warning(f"Connection error fetching CVE score for {cve_id}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        logger.warning(f"Request error fetching CVE score for {cve_id}: {e}")
        return None
    except (KeyError, IndexError, ValueError) as e:
        logger.warning(f"Error parsing CVE response for {cve_id}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Unexpected error fetching CVE score for {cve_id}: {e}")
        return None

