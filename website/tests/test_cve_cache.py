"""
Tests for CVE caching utilities.
"""

from decimal import Decimal
from unittest.mock import Mock, patch

import requests
from django.core.cache import cache
from django.test import TestCase

from website.cache.cve_cache import (
    CACHE_NONE,
    fetch_cve_score_from_api,
    get_cached_cve_score,
    get_cve_cache_key,
    normalize_cve_id,
)


class TestNormalizeCveId(TestCase):
    """Test CVE ID normalization and validation."""

    def setUp(self):
        """Clear cache before each test."""
        cache.clear()

    def tearDown(self):
        """Clear cache after each test."""
        cache.clear()

    def test_valid_cve_id(self):
        """Test that valid CVE IDs are normalized correctly."""
        self.assertEqual(normalize_cve_id("CVE-2024-1234"), "CVE-2024-1234")
        self.assertEqual(normalize_cve_id("cve-2024-1234"), "CVE-2024-1234")
        self.assertEqual(normalize_cve_id("  CVE-2024-1234  "), "CVE-2024-1234")

    def test_invalid_cve_id_format(self):
        """Test that invalid CVE IDs return empty string."""
        self.assertEqual(normalize_cve_id("INVALID-ID"), "")
        self.assertEqual(normalize_cve_id("CVE-2024"), "")
        self.assertEqual(normalize_cve_id("CVE-2024-123"), "")  # Too short
        self.assertEqual(normalize_cve_id("CVE-2024-12345678"), "")  # Too long
        self.assertEqual(normalize_cve_id("not-a-cve"), "")

    def test_empty_cve_id(self):
        """Test that empty/None CVE IDs return empty string."""
        self.assertEqual(normalize_cve_id(""), "")
        self.assertEqual(normalize_cve_id(None), "")


class TestGetCveCacheKey(TestCase):
    """Test cache key generation."""

    def setUp(self):
        """Clear cache before each test."""
        cache.clear()

    def tearDown(self):
        """Clear cache after each test."""
        cache.clear()

    def test_cache_key_format(self):
        """Test that cache key is generated correctly."""
        cve_id = "CVE-2024-1234"
        expected = "cve:CVE-2024-1234"
        self.assertEqual(get_cve_cache_key(cve_id), expected)

    def test_cache_key_normalizes_whitespace_and_case(self):
        """Cache keys should ignore casing/whitespace differences."""
        cve_id = "  cve-2024-1234 "
        expected = "cve:CVE-2024-1234"
        self.assertEqual(get_cve_cache_key(cve_id), expected)


class TestFetchCveScoreFromApi(TestCase):
    """Test direct API fetching (without cache)."""

    def setUp(self):
        """Clear cache before each test."""
        cache.clear()

    def tearDown(self):
        """Clear cache after each test."""
        cache.clear()

    @patch("website.cache.cve_cache.requests.get")
    def test_successful_fetch_with_cvss_v3_1(self, mock_get):
        """Test successful CVE score fetch with CVSS v3.1."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "resultsPerPage": 1,
            "vulnerabilities": [
                {
                    "cve": {
                        "metrics": {
                            "cvssMetricV31": [
                                {
                                    "cvssData": {
                                        "baseScore": 7.5,
                                    }
                                }
                            ]
                        }
                    }
                }
            ],
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result, had_error = fetch_cve_score_from_api("CVE-2024-1234")

        self.assertEqual(result, Decimal("7.5"))
        self.assertFalse(had_error)
        self.assertEqual(mock_get.call_count, 1)
        self.assertIn("CVE-2024-1234", mock_get.call_args[0][0])

    @patch("website.cache.cve_cache.requests.get")
    def test_successful_fetch_with_cvss_v2(self, mock_get):
        """Test successful CVE score fetch with CVSS v2.0."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "resultsPerPage": 1,
            "vulnerabilities": [
                {
                    "cve": {
                        "metrics": {
                            "cvssMetricV2": [
                                {
                                    "cvssData": {
                                        "baseScore": 6.8,
                                    }
                                }
                            ]
                        }
                    }
                }
            ],
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result, had_error = fetch_cve_score_from_api("CVE-2024-5678")

        self.assertEqual(result, Decimal("6.8"))
        self.assertFalse(had_error)

    @patch("website.cache.cve_cache.requests.get")
    def test_no_results_found(self, mock_get):
        """Test when API returns no results."""
        mock_response = Mock()
        mock_response.json.return_value = {"resultsPerPage": 0}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result, had_error = fetch_cve_score_from_api("CVE-2024-9999")

        self.assertIsNone(result)
        self.assertFalse(had_error)  # Valid response: CVE not found

    @patch("website.cache.cve_cache.requests.get")
    def test_empty_vulnerabilities(self, mock_get):
        """Test when vulnerabilities array is empty."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "resultsPerPage": 1,
            "vulnerabilities": [],
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result, had_error = fetch_cve_score_from_api("CVE-2024-1234")

        self.assertIsNone(result)
        self.assertFalse(had_error)  # Valid response: no vulnerabilities

    @patch("website.cache.cve_cache.requests.get")
    def test_missing_metrics(self, mock_get):
        """Test when metrics are missing from response."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "resultsPerPage": 1,
            "vulnerabilities": [{"cve": {}}],
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result, had_error = fetch_cve_score_from_api("CVE-2024-1234")

        self.assertIsNone(result)
        self.assertFalse(had_error)  # Valid response: no metrics

    @patch("website.cache.cve_cache.requests.get")
    def test_missing_base_score(self, mock_get):
        """Test when baseScore is missing from response."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "resultsPerPage": 1,
            "vulnerabilities": [
                {
                    "cve": {
                        "metrics": {
                            "cvssMetricV31": [{"cvssData": {}}],
                        }
                    }
                }
            ],
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result, had_error = fetch_cve_score_from_api("CVE-2024-1234")

        self.assertIsNone(result)
        self.assertFalse(had_error)  # Valid response: no baseScore

    @patch("website.cache.cve_cache.requests.get")
    def test_timeout_exception(self, mock_get):
        """Test timeout handling."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")

        result, had_error = fetch_cve_score_from_api("CVE-2024-1234")

        self.assertIsNone(result)
        self.assertTrue(had_error)  # Error: timeout

    @patch("website.cache.cve_cache.time.sleep", autospec=True)
    @patch("website.cache.cve_cache.requests.get")
    def test_rate_limit_429(self, mock_get, mock_sleep):
        """Test rate limiting (429) handling."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_http_error = requests.exceptions.HTTPError()
        mock_http_error.response = mock_response
        mock_get.side_effect = mock_http_error

        result, had_error = fetch_cve_score_from_api("CVE-2024-1234")

        self.assertIsNone(result)
        self.assertTrue(had_error)  # Error: rate limit after retries
        # Default max retries is 3
        self.assertEqual(mock_get.call_count, 3)
        # Retries happen max_retries - 1 times (final attempt does not sleep afterward)
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("website.cache.cve_cache.requests.get")
    def test_http_error_non_429(self, mock_get):
        """Test non-429 HTTP error handling."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_http_error = requests.exceptions.HTTPError("Server Error")
        mock_http_error.response = mock_response
        mock_get.side_effect = mock_http_error

        result, had_error = fetch_cve_score_from_api("CVE-2024-1234")

        self.assertIsNone(result)
        self.assertTrue(had_error)  # Error: HTTP 500 after retries

    @patch("website.cache.cve_cache.requests.get")
    def test_connection_error(self, mock_get):
        """Test connection error handling."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        result, had_error = fetch_cve_score_from_api("CVE-2024-1234")

        self.assertIsNone(result)
        self.assertTrue(had_error)  # Error: connection failed

    @patch("website.cache.cve_cache.requests.get")
    def test_request_exception(self, mock_get):
        """Test generic RequestException handling."""
        mock_get.side_effect = requests.exceptions.RequestException("Request failed")

        result, had_error = fetch_cve_score_from_api("CVE-2024-1234")

        self.assertIsNone(result)
        self.assertTrue(had_error)  # Error: request exception

    @patch("website.cache.cve_cache.requests.get")
    def test_json_parsing_error(self, mock_get):
        """Test JSON parsing error handling."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result, had_error = fetch_cve_score_from_api("CVE-2024-1234")

        self.assertIsNone(result)
        self.assertTrue(had_error)  # Error: JSON parsing failed

    @patch("website.cache.cve_cache.requests.get")
    def test_decimal_conversion_error_handling(self, mock_get):
        """Test error handling when baseScore cannot be converted to Decimal."""
        mock_response = Mock()
        # Return structure with invalid baseScore that can't be converted to Decimal
        mock_response.json.return_value = {
            "resultsPerPage": 1,
            "vulnerabilities": [
                {
                    "cve": {
                        "metrics": {
                            "cvssMetricV31": [
                                {
                                    "cvssData": {
                                        "baseScore": "invalid_number",  # Will cause Decimal conversion error
                                    }
                                }
                            ],
                        }
                    }
                }
            ],
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result, had_error = fetch_cve_score_from_api("CVE-2024-1234")

        self.assertIsNone(result)
        self.assertTrue(had_error)  # Error: malformed response (ValueError from Decimal conversion)

    @patch("website.cache.cve_cache.requests.get")
    def test_index_error_handling(self, mock_get):
        """Test IndexError handling when accessing list index fails."""
        mock_response = Mock()
        # Create a scenario where accessing [0] raises IndexError
        # We need to mock a list-like object that passes len() but fails on [0]

        class IndexErrorList:
            def __len__(self):
                return 1  # Passes len() check

            def __getitem__(self, key):
                raise IndexError

        mock_response.json.return_value = {
            "resultsPerPage": 1,
            "vulnerabilities": [
                {
                    "cve": {
                        "metrics": {
                            "cvssMetricV31": IndexErrorList(),
                        }
                    }
                }
            ],
        }
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result, had_error = fetch_cve_score_from_api("CVE-2024-1234")

        self.assertIsNone(result)
        self.assertTrue(had_error)  # Error: IndexError accessing list

    def test_none_input(self):
        """Test that None input returns None without calling API."""
        result, had_error = fetch_cve_score_from_api(None)

        self.assertIsNone(result)
        self.assertFalse(had_error)  # Valid: invalid CVE format (can cache as "not found")

    def test_empty_string_input(self):
        """Test that empty string input returns None without calling API."""
        result, had_error = fetch_cve_score_from_api("")

        self.assertIsNone(result)
        self.assertFalse(had_error)  # Valid: invalid CVE format (can cache as "not found")

    @patch("website.cache.cve_cache.requests.get")
    def test_invalid_cve_id_format(self, mock_get):
        """Test with invalid CVE ID format - should return None without API call."""
        result, had_error = fetch_cve_score_from_api("INVALID-ID")

        self.assertIsNone(result)
        self.assertFalse(had_error)  # Valid: invalid CVE format (can cache as "not found")
        # API should not be called for invalid CVE IDs (validation happens first)
        mock_get.assert_not_called()


class TestGetCachedCveScore(TestCase):
    """Test cached CVE score retrieval."""

    def setUp(self):
        """Clear cache before each test."""
        cache.clear()

    def tearDown(self):
        """Clear cache after each test."""
        cache.clear()

    @patch("website.cache.cve_cache.fetch_cve_score_from_api")
    def test_cache_hit(self, mock_fetch):
        """Test that cached score is returned without API call."""
        cve_id = "CVE-2024-1234"
        cached_score = Decimal("7.5")
        cache_key = get_cve_cache_key(cve_id)

        # Set cache with actual score (not sentinel)
        cache.set(cache_key, cached_score, timeout=86400)

        # Get from cache
        result = get_cached_cve_score(cve_id)

        self.assertEqual(result, cached_score)
        mock_fetch.assert_not_called()

    @patch("website.cache.cve_cache.fetch_cve_score_from_api")
    def test_cache_miss_then_hit(self, mock_fetch):
        """Test cache miss followed by cache hit."""
        cve_id = "CVE-2024-1234"
        api_score = Decimal("8.2")
        mock_fetch.return_value = (api_score, False)  # Successful fetch

        # First call - cache miss, should call API
        result1 = get_cached_cve_score(cve_id)

        self.assertEqual(result1, api_score)
        self.assertEqual(mock_fetch.call_count, 1)

        # Second call - cache hit, should not call API
        mock_fetch.reset_mock()
        result2 = get_cached_cve_score(cve_id)

        self.assertEqual(result2, api_score)
        mock_fetch.assert_not_called()

    @patch("website.cache.cve_cache.fetch_cve_score_from_api")
    def test_cache_miss_api_returns_none(self, mock_fetch):
        """Test that None results are cached using sentinel value to avoid repeated API calls."""
        cve_id = "CVE-2024-9999"
        mock_fetch.return_value = (None, False)  # Valid response: CVE not found

        # First call - cache miss, should call API
        result1 = get_cached_cve_score(cve_id)
        self.assertIsNone(result1)
        self.assertEqual(mock_fetch.call_count, 1)

        # Verify None was cached with sentinel value
        cache_key = get_cve_cache_key(cve_id)
        cached_value = cache.get(cache_key)
        self.assertIsNotNone(cached_value, "Cache should contain sentinel value, not None")
        self.assertEqual(cached_value, CACHE_NONE, f"Expected {CACHE_NONE}, got {cached_value}")

        # Second call - cache hit, should NOT call API again
        mock_fetch.reset_mock()
        result2 = get_cached_cve_score(cve_id)
        self.assertIsNone(result2)
        # None results are now cached, so API should not be called again
        mock_fetch.assert_not_called()

    @patch("website.cache.cve_cache.fetch_cve_score_from_api")
    def test_cache_error_fallback_to_api(self, mock_fetch):
        """Test that cache errors fall back to API."""
        cve_id = "CVE-2024-1234"
        api_score = Decimal("6.5")
        mock_fetch.return_value = (api_score, False)  # Successful fetch

        # Simulate cache error by patching cache.get to raise exception
        with patch("website.cache.cve_cache.cache.get", side_effect=Exception("Cache error")):
            result = get_cached_cve_score(cve_id)

        self.assertEqual(result, api_score)
        mock_fetch.assert_called_once_with(cve_id)

    @patch("website.cache.cve_cache.fetch_cve_score_from_api")
    def test_cache_set_error_continues(self, mock_fetch):
        """Test that cache set errors don't break the flow."""
        cve_id = "CVE-2024-1234"
        api_score = Decimal("9.1")
        mock_fetch.return_value = (api_score, False)  # Successful fetch

        # Simulate cache.set error
        with patch("website.cache.cve_cache.cache.set", side_effect=Exception("Cache set error")):
            result = get_cached_cve_score(cve_id)

        self.assertEqual(result, api_score)

    def test_none_input(self):
        """Test that None input returns None without cache or API calls."""
        with patch("website.cache.cve_cache.fetch_cve_score_from_api") as mock_fetch:
            result = get_cached_cve_score(None)

        self.assertIsNone(result)
        mock_fetch.assert_not_called()

    def test_empty_string_input(self):
        """Test that empty string input returns None without cache or API calls."""
        with patch("website.cache.cve_cache.fetch_cve_score_from_api") as mock_fetch:
            result = get_cached_cve_score("")

        self.assertIsNone(result)
        mock_fetch.assert_not_called()

    @patch("website.cache.cve_cache.fetch_cve_score_from_api")
    def test_timeout_propagates_correctly(self, mock_fetch):
        """Test that timeout from API is handled correctly in cached function."""
        cve_id = "CVE-2024-1234"
        mock_fetch.return_value = (None, True)  # Error: timeout (don't cache)

        result = get_cached_cve_score(cve_id)

        self.assertIsNone(result)
        mock_fetch.assert_called_once_with(cve_id)

    @patch("website.cache.cve_cache.fetch_cve_score_from_api")
    def test_cve_id_normalization_prevents_duplicate_fetches(self, mock_fetch):
        """Whitespace/case variations should map to same cache entry."""
        api_score = Decimal("4.2")
        mock_fetch.return_value = (api_score, False)  # Successful fetch

        first_result = get_cached_cve_score("  cve-2024-4242  ")
        self.assertEqual(first_result, api_score)
        self.assertEqual(mock_fetch.call_count, 1)
        mock_fetch.reset_mock()

        second_result = get_cached_cve_score("CVE-2024-4242")
        self.assertEqual(second_result, api_score)
        mock_fetch.assert_not_called()
