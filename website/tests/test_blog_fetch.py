import requests

from unittest.mock import MagicMock, patch

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
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = [
            {
                "title": "Test Post",
                "url": "https://dev.to/test",
                "cover_image": "https://dev.to/image.png",
                "description": "Test description",
                "user": {"name": "Test User"},
                "published_at": "2026-02-24T12:00:00Z",
            }
        ]
        mock_get.return_value = mock_response

        articles = fetch_devto_articles()

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["user_name"], "Test User")
        self.assertEqual(articles[0]["published_at"], "2026-02-24")

        # Verify caching occurred
        self.assertIsNotNone(cache.get(self.cache_key))

    @patch("website.views.core.requests.get")
    def test_fetch_cache_hit(self, mock_get):
        """Test cached data is returned without API call"""

        cache.set(self.cache_key, [{"title": "Cached"}])

        articles = fetch_devto_articles()

        self.assertEqual(articles[0]["title"], "Cached")
        mock_get.assert_not_called()

    @patch("website.views.core.requests.get")
    def test_fetch_json_error(self, mock_get):
        """Test handling of invalid JSON responses"""

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_get.return_value = mock_response

        articles = fetch_devto_articles()

        self.assertEqual(articles, [])
        self.assertEqual(cache.get(self.cache_key), [])

    @patch("website.views.core.requests.get")
    def test_fetch_unexpected_format(self, mock_get):
        """Test handling when API returns unexpected data structure"""

        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"error": "wrong format"}
        mock_get.return_value = mock_response

        articles = fetch_devto_articles()

        self.assertEqual(articles, [])

    @patch("website.views.core.requests.get")
    def test_fetch_network_exception(self, mock_get):
        """Test handling of network timeout or request failure"""

        mock_get.side_effect = requests.RequestException("Timeout")

        articles = fetch_devto_articles()

        self.assertEqual(articles, [])
        self.assertEqual(cache.get(self.cache_key), [])