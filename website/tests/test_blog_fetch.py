from unittest.mock import MagicMock, patch

import requests
from django.core.cache import cache
from django.test import TestCase

from website.views.core import fetch_devto_articles


class DevToBlogTests(TestCase):
    """Test suite for Dev.to blog fetching logic"""

    def setUp(self):
        self.cache_key = "devto_articles"
        cache.clear()

    @patch("website.views.core.requests.get")
    def test_fetch_success(self, mock_get):
        """Test successful API fetch and refined article output"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "title": "Test Post",
                "url": "https://dev.to/test",
                "user": {"name": "Test User"},
                "published_at": "2026-02-24T12:00:00Z",
            }
        ]
        mock_get.return_value = mock_response

        articles = fetch_devto_articles()

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["title"], "Test Post")

        cached_data = cache.get(self.cache_key)
        self.assertEqual(len(cached_data), 1)
        self.assertEqual(cached_data[0]["user_name"], "Test User")

    @patch("website.views.core.requests.get")
    def test_fetch_cache_logic(self, mock_get):
        """
        Note: Since fetch_devto_articles now always performs a fetch
        to refresh the cache, we test that it overwrites existing data.
        """
        cache.set(self.cache_key, [{"title": "Old Data"}])

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"title": "New Data", "url": "https://dev.to/new"}]
        mock_get.return_value = mock_response

        fetch_devto_articles()

        self.assertEqual(cache.get(self.cache_key)[0]["title"], "New Data")

    @patch("website.views.core.requests.get")
    def test_fetch_json_error(self, mock_get):
        """Test handling of invalid JSON responses"""
        mock_response = MagicMock()
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        articles = fetch_devto_articles()

        self.assertEqual(articles, [])
        self.assertEqual(cache.get(self.cache_key), [])

    @patch("website.views.core.requests.get")
    def test_fetch_unexpected_format(self, mock_get):
        """Test handling when API returns unexpected data structure"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "wrong format"}
        mock_get.return_value = mock_response

        articles = fetch_devto_articles()

        self.assertEqual(articles, [])
        self.assertEqual(cache.get(self.cache_key), [])

    @patch("website.views.core.requests.get")
    def test_fetch_network_exception(self, mock_get):
        """Test handling of network timeout or request failure"""
        mock_get.side_effect = requests.RequestException("Timeout")

        articles = fetch_devto_articles()

        self.assertEqual(articles, [])
        self.assertEqual(cache.get(self.cache_key), [])
