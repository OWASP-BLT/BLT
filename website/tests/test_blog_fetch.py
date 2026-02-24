from unittest.mock import MagicMock, patch

import requests
from django.core.cache import cache
from django.test import TestCase

from website.views.core import fetch_devto_articles


class DevToBlogTests(TestCase):
    """Test suite for Dev.to blog fetching logic addressing Peer Review & Sentry Bot"""

    def setUp(self):
        self.cache_key = "devto_articles"
        cache.clear()

    @patch("website.views.core.requests.get")
    def test_fetch_cache_hit(self, mock_get):
        """Test that function returns cached data immediately without calling API (Point 1392)"""
        cache.set(self.cache_key, [{"title": "Cached Title"}])

        articles = fetch_devto_articles()

        self.assertEqual(articles[0]["title"], "Cached Title")
        mock_get.assert_not_called()

    @patch("website.views.core.requests.get")
    def test_fetch_success(self, mock_get):
        """Test successful API fetch, refined output, and caching"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "title": "Test Post",
                "url": "https://dev.to/test",
                "cover_image": "https://dev.to/img.png",
                "user": {"name": "Test User"},
                "published_at": "2026-02-24T12:00:00Z",
            }
        ]
        mock_get.return_value = mock_response

        articles = fetch_devto_articles()

        self.assertEqual(len(articles), 1)
        self.assertEqual(articles[0]["user_name"], "Test User")
        self.assertIsNotNone(cache.get(self.cache_key))

    @patch("website.views.core.requests.get")
    def test_fetch_insecure_image_validation(self, mock_get):
        """Test that non-HTTPS cover images are stripped (Addressing Sentry finding)"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "title": "Insecure Post",
                "url": "https://dev.to/link",
                "cover_image": "http://insecure.com/img.png",
            }
        ]
        mock_get.return_value = mock_response

        articles = fetch_devto_articles()

        self.assertEqual(articles[0]["cover_image"], "")
        self.assertEqual(articles[0]["url"], "https://dev.to/link")

    @patch("website.views.core.requests.get")
    def test_fetch_unexpected_format(self, mock_get):
        """Test handling when API returns non-list structure (Point 1410/1412)"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "not a list"}
        mock_get.return_value = mock_response

        articles = fetch_devto_articles()

        self.assertEqual(articles, [])
        self.assertEqual(cache.get(self.cache_key), [])

    @patch("website.views.core.requests.get")
    def test_fetch_network_exception(self, mock_get):
        """Test handling of network failure and failure-cache setting"""
        mock_get.side_effect = requests.RequestException("Timeout")

        articles = fetch_devto_articles()

        self.assertEqual(articles, [])
        self.assertEqual(cache.get(self.cache_key), [])
