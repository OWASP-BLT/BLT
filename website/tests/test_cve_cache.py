"""
Tests for CVE caching utilities.
"""
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
import requests
from django.core.cache import cache

from website.cache.cve_cache import CACHE_NONE, fetch_cve_score_from_api, get_cached_cve_score, get_cve_cache_key


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before and after each test."""
    cache.clear()
    yield
    cache.clear()


class TestGetCveCacheKey:
    """Test cache key generation."""

    def test_cache_key_format(self):
        """Test that cache key is generated correctly."""
        cve_id = "CVE-2024-1234"
        expected = "cve:CVE-2024-1234"
        assert get_cve_cache_key(cve_id) == expected


class TestFetchCveScoreFromApi:
    """Test direct API fetching (without cache)."""

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

        result = fetch_cve_score_from_api("CVE-2024-1234")

        assert result == Decimal("7.5")
        mock_get.assert_called_once()
        assert "CVE-2024-1234" in mock_get.call_args[0][0]

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

        result = fetch_cve_score_from_api("CVE-2024-5678")

        assert result == Decimal("6.8")

    @patch("website.cache.cve_cache.requests.get")
    def test_no_results_found(self, mock_get):
        """Test when API returns no results."""
        mock_response = Mock()
        mock_response.json.return_value = {"resultsPerPage": 0}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = fetch_cve_score_from_api("CVE-2024-9999")

        assert result is None

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

        result = fetch_cve_score_from_api("CVE-2024-1234")

        assert result is None

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

        result = fetch_cve_score_from_api("CVE-2024-1234")

        assert result is None

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

        result = fetch_cve_score_from_api("CVE-2024-1234")

        assert result is None

    @patch("website.cache.cve_cache.requests.get")
    def test_timeout_exception(self, mock_get, caplog):
        """Test timeout handling."""
        mock_get.side_effect = requests.exceptions.Timeout("Connection timeout")

        result = fetch_cve_score_from_api("CVE-2024-1234")

        assert result is None
        assert "Timeout fetching CVE score" in caplog.text
        assert "CVE-2024-1234" in caplog.text

    @patch("website.cache.cve_cache.requests.get")
    def test_rate_limit_429(self, mock_get, caplog):
        """Test rate limiting (429) handling."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_http_error = requests.exceptions.HTTPError()
        mock_http_error.response = mock_response
        mock_get.side_effect = mock_http_error

        result = fetch_cve_score_from_api("CVE-2024-1234")

        assert result is None
        assert "Rate limit exceeded" in caplog.text
        assert "CVE-2024-1234" in caplog.text

    @patch("website.cache.cve_cache.requests.get")
    def test_http_error_non_429(self, mock_get, caplog):
        """Test non-429 HTTP error handling."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_http_error = requests.exceptions.HTTPError("Server Error")
        mock_http_error.response = mock_response
        mock_get.side_effect = mock_http_error

        result = fetch_cve_score_from_api("CVE-2024-1234")

        assert result is None
        assert "HTTP error fetching CVE score" in caplog.text
        assert "CVE-2024-1234" in caplog.text

    @patch("website.cache.cve_cache.requests.get")
    def test_connection_error(self, mock_get, caplog):
        """Test connection error handling."""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        result = fetch_cve_score_from_api("CVE-2024-1234")

        assert result is None
        assert "Connection error fetching CVE score" in caplog.text
        assert "CVE-2024-1234" in caplog.text

    @patch("website.cache.cve_cache.requests.get")
    def test_request_exception(self, mock_get, caplog):
        """Test generic RequestException handling."""
        mock_get.side_effect = requests.exceptions.RequestException("Request failed")

        result = fetch_cve_score_from_api("CVE-2024-1234")

        assert result is None
        assert "Request error fetching CVE score" in caplog.text
        assert "CVE-2024-1234" in caplog.text

    @patch("website.cache.cve_cache.requests.get")
    def test_json_parsing_error(self, mock_get, caplog):
        """Test JSON parsing error handling."""
        mock_response = Mock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = fetch_cve_score_from_api("CVE-2024-1234")

        assert result is None
        assert "Error parsing CVE response" in caplog.text


    @patch("website.cache.cve_cache.requests.get")
    def test_decimal_conversion_error_handling(self, mock_get, caplog):
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

        result = fetch_cve_score_from_api("CVE-2024-1234")

        assert result is None
        # Decimal conversion errors are caught by generic Exception handler
        assert "Unexpected error fetching CVE score" in caplog.text

    @patch("website.cache.cve_cache.requests.get")
    def test_index_error_handling(self, mock_get, caplog):
        """Test IndexError handling when accessing list index fails."""
        mock_response = Mock()
        # Create a scenario where accessing [0] raises IndexError
        # We need to mock a list-like object that passes len() but fails on [0]
        from unittest.mock import MagicMock
        
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

        result = fetch_cve_score_from_api("CVE-2024-1234")

        assert result is None
        assert "Error parsing CVE response" in caplog.text

    def test_none_input(self):
        """Test that None input returns None without calling API."""
        result = fetch_cve_score_from_api(None)

        assert result is None

    def test_empty_string_input(self):
        """Test that empty string input returns None without calling API."""
        result = fetch_cve_score_from_api("")

        assert result is None

    @patch("website.cache.cve_cache.requests.get")
    def test_invalid_cve_id_format(self, mock_get):
        """Test with invalid CVE ID format."""
        mock_response = Mock()
        mock_response.json.return_value = {"resultsPerPage": 0}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = fetch_cve_score_from_api("INVALID-ID")

        assert result is None
        mock_get.assert_called_once()


class TestGetCachedCveScore:
    """Test cached CVE score retrieval."""

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

        assert result == cached_score
        mock_fetch.assert_not_called()

    @patch("website.cache.cve_cache.fetch_cve_score_from_api")
    def test_cache_miss_then_hit(self, mock_fetch):
        """Test cache miss followed by cache hit."""
        cve_id = "CVE-2024-1234"
        api_score = Decimal("8.2")
        mock_fetch.return_value = api_score

        # First call - cache miss, should call API
        result1 = get_cached_cve_score(cve_id)

        assert result1 == api_score
        assert mock_fetch.call_count == 1

        # Second call - cache hit, should not call API
        mock_fetch.reset_mock()
        result2 = get_cached_cve_score(cve_id)

        assert result2 == api_score
        mock_fetch.assert_not_called()

    @patch("website.cache.cve_cache.fetch_cve_score_from_api")
    def test_cache_miss_api_returns_none(self, mock_fetch):
        """Test that None results are cached using sentinel value to avoid repeated API calls."""
        cve_id = "CVE-2024-9999"
        mock_fetch.return_value = None

        # First call - cache miss, should call API
        result1 = get_cached_cve_score(cve_id)
        assert result1 is None
        assert mock_fetch.call_count == 1

        # Verify None was cached with sentinel value
        cache_key = get_cve_cache_key(cve_id)
        cached_value = cache.get(cache_key)
        assert cached_value is not None, "Cache should contain sentinel value, not None"
        assert cached_value == CACHE_NONE, f"Expected {CACHE_NONE}, got {cached_value}"

        # Second call - cache hit, should NOT call API again
        mock_fetch.reset_mock()
        result2 = get_cached_cve_score(cve_id)
        assert result2 is None
        # None results are now cached, so API should not be called again
        mock_fetch.assert_not_called()

    @patch("website.cache.cve_cache.fetch_cve_score_from_api")
    def test_cache_error_fallback_to_api(self, mock_fetch, caplog):
        """Test that cache errors fall back to API."""
        cve_id = "CVE-2024-1234"
        api_score = Decimal("6.5")
        mock_fetch.return_value = api_score

        # Simulate cache error by patching cache.get to raise exception
        with patch("website.cache.cve_cache.cache.get", side_effect=Exception("Cache error")):
            result = get_cached_cve_score(cve_id)

        assert result == api_score
        assert "Error reading from cache" in caplog.text
        mock_fetch.assert_called_once_with(cve_id)

    @patch("website.cache.cve_cache.fetch_cve_score_from_api")
    def test_cache_set_error_continues(self, mock_fetch, caplog):
        """Test that cache set errors don't break the flow."""
        cve_id = "CVE-2024-1234"
        api_score = Decimal("9.1")
        mock_fetch.return_value = api_score

        # Simulate cache.set error
        with patch("website.cache.cve_cache.cache.set", side_effect=Exception("Cache set error")):
            result = get_cached_cve_score(cve_id)

        assert result == api_score
        assert "Error caching CVE score" in caplog.text

    def test_none_input(self):
        """Test that None input returns None without cache or API calls."""
        with patch("website.cache.cve_cache.fetch_cve_score_from_api") as mock_fetch:
            result = get_cached_cve_score(None)

        assert result is None
        mock_fetch.assert_not_called()

    def test_empty_string_input(self):
        """Test that empty string input returns None without cache or API calls."""
        with patch("website.cache.cve_cache.fetch_cve_score_from_api") as mock_fetch:
            result = get_cached_cve_score("")

        assert result is None
        mock_fetch.assert_not_called()

    @patch("website.cache.cve_cache.fetch_cve_score_from_api")
    def test_timeout_propagates_correctly(self, mock_fetch):
        """Test that timeout from API is handled correctly in cached function."""
        cve_id = "CVE-2024-1234"
        mock_fetch.return_value = None

        result = get_cached_cve_score(cve_id)

        assert result is None
        mock_fetch.assert_called_once_with(cve_id)

