import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse, HttpResponseForbidden
from django.test import TestCase

from blt.middleware.ip_restrict import IPRestrictMiddleware
from website.models import IP, Blocked


def is_sqlite():
    """Check if the test database is SQLite."""
    return settings.DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3"


class IPRestrictMiddlewareTestCase(TestCase):
    """Test case for the IPRestrictMiddleware."""

    def setUp(self):
        """Set up test data for the middleware tests."""
        # Clear cache before each test
        cache.clear()

        # Create blocked IP
        self.blocked_ip = Blocked.objects.create(address="192.168.1.1", reason_for_block="Test IP block")

        # Create blocked IP network
        self.blocked_network = Blocked.objects.create(ip_network="10.0.0.0/24", reason_for_block="Test network block")

        # Create blocked user agent
        self.blocked_agent = Blocked.objects.create(
            user_agent_string="BadBot", reason_for_block="Test user agent block"
        )

        # Create a mock get_response
        self.mock_get_response = MagicMock(return_value=HttpResponse("OK"))
        self.middleware = IPRestrictMiddleware(self.mock_get_response)

    def tearDown(self):
        """Clean up test data."""
        Blocked.objects.all().delete()
        IP.objects.all().delete()
        cache.clear()

    def _create_mock_request(self, ip="1.2.3.4", user_agent="TestAgent", path="/test/"):
        """Helper method to create a mock request."""
        request = MagicMock()
        request.META = {
            "REMOTE_ADDR": ip,
            "HTTP_USER_AGENT": user_agent,
            "HTTP_X_FORWARDED_FOR": "",
        }
        request.path = path
        return request

    def test_sync_middleware_allows_normal_request(self):
        """Test that the synchronous middleware allows normal requests."""
        request = self._create_mock_request(ip="1.2.3.4", user_agent="NormalBrowser")

        # Call the middleware
        response = self.middleware(request)

        # Assert the request was allowed
        self.assertEqual(response.status_code, 200)
        self.mock_get_response.assert_called_once_with(request)

        # Verify IP was recorded
        ip_record = IP.objects.filter(address="1.2.3.4", path="/test/").first()
        self.assertIsNotNone(ip_record)
        self.assertEqual(ip_record.count, 1)
        self.assertEqual(ip_record.agent, "NormalBrowser")

    def test_sync_middleware_blocks_ip(self):
        """Test that the synchronous middleware blocks a blocked IP."""
        request = self._create_mock_request(ip="192.168.1.1", user_agent="NormalBrowser")

        # Call the middleware
        response = self.middleware(request)

        # Assert the request was blocked
        self.assertIsInstance(response, HttpResponseForbidden)
        self.mock_get_response.assert_not_called()

        # Verify block count was incremented
        blocked = Blocked.objects.get(address="192.168.1.1")
        self.assertEqual(blocked.count, 2)

    def test_sync_middleware_blocks_ip_in_network(self):
        """Test that the synchronous middleware blocks an IP in a blocked network."""
        request = self._create_mock_request(ip="10.0.0.50", user_agent="NormalBrowser")

        # Call the middleware
        response = self.middleware(request)

        # Assert the request was blocked
        self.assertIsInstance(response, HttpResponseForbidden)
        self.mock_get_response.assert_not_called()

        # Verify block count was incremented for the network
        blocked = Blocked.objects.get(ip_network="10.0.0.0/24")
        self.assertEqual(blocked.count, 2)

    def test_sync_middleware_blocks_user_agent(self):
        """Test that the synchronous middleware blocks a blocked user agent."""
        request = self._create_mock_request(ip="1.2.3.4", user_agent="BadBot/1.0")

        # Call the middleware
        response = self.middleware(request)

        # Assert the request was blocked
        self.assertIsInstance(response, HttpResponseForbidden)
        self.mock_get_response.assert_not_called()

        # Verify block count was incremented
        blocked = Blocked.objects.get(user_agent_string="BadBot")
        self.assertEqual(blocked.count, 2)

    def test_sync_middleware_increments_ip_count(self):
        """Test that the synchronous middleware increments IP count for repeated visits."""
        request = self._create_mock_request(ip="1.2.3.4", user_agent="NormalBrowser")

        # Call the middleware multiple times
        self.middleware(request)
        self.middleware(request)
        self.middleware(request)

        # Verify IP count was incremented
        ip_record = IP.objects.filter(address="1.2.3.4", path="/test/").first()
        self.assertIsNotNone(ip_record)
        self.assertEqual(ip_record.count, 3)

    def test_sync_middleware_x_forwarded_for(self):
        """Test that the synchronous middleware uses X-Forwarded-For header."""
        request = MagicMock()
        request.META = {
            "REMOTE_ADDR": "5.6.7.8",
            "HTTP_USER_AGENT": "NormalBrowser",
            "HTTP_X_FORWARDED_FOR": "192.168.1.1, 5.6.7.8",
        }
        request.path = "/test/"

        # Call the middleware
        response = self.middleware(request)

        # Assert the request was blocked (because X-Forwarded-For contains blocked IP)
        self.assertIsInstance(response, HttpResponseForbidden)
        self.mock_get_response.assert_not_called()

    def test_async_middleware_basic(self):
        """Test basic async middleware functionality."""
        # Note: Async tests may fail with SQLite due to database locking issues.
        # They work fine with PostgreSQL or other databases that support concurrent access.
        if is_sqlite():
            self.skipTest("Async tests are skipped with SQLite due to database locking limitations")

        async def test_async():
            # Clear cache to avoid stale data
            cache.clear()

            request = self._create_mock_request(ip="2.3.4.5", user_agent="AsyncBrowser")

            # Create async mock for get_response
            async_mock = AsyncMock(return_value=HttpResponse("OK"))
            middleware = IPRestrictMiddleware(async_mock)

            # Call the middleware
            response = await middleware.__acall__(request)

            # Assert the request was allowed
            assert response.status_code == 200
            async_mock.assert_called_once_with(request)

        # Run the async test
        asyncio.run(test_async())

    def test_record_ip_helper_method(self):
        """Test the _record_ip helper method directly."""
        # First call - create new record
        self.middleware._record_ip("7.8.9.10", "TestAgent", "/path1/")

        ip_record = IP.objects.filter(address="7.8.9.10", path="/path1/").first()
        self.assertIsNotNone(ip_record)
        self.assertEqual(ip_record.count, 1)
        self.assertEqual(ip_record.agent, "TestAgent")

        # Second call - increment count
        self.middleware._record_ip("7.8.9.10", "TestAgent2", "/path1/")

        ip_record = IP.objects.filter(address="7.8.9.10", path="/path1/").first()
        self.assertEqual(ip_record.count, 2)
        self.assertEqual(ip_record.agent, "TestAgent2")

    def test_record_ip_max_count_limit(self):
        """Test that IP count doesn't exceed MAX_COUNT."""
        from blt.middleware.ip_restrict import MAX_COUNT

        # Create a record at max count
        IP.objects.create(address="8.9.10.11", agent="Test", count=MAX_COUNT, path="/test/")

        # Try to increment it
        self.middleware._record_ip("8.9.10.11", "Test", "/test/")

        # Verify count stayed at MAX_COUNT
        ip_record = IP.objects.filter(address="8.9.10.11", path="/test/").first()
        self.assertEqual(ip_record.count, MAX_COUNT)

    def test_cache_usage(self):
        """Test that the middleware uses caching for blocked items."""
        with patch.object(self.middleware, "get_cached_data") as mock_cache:
            mock_cache.return_value = []

            # Call blocked_ips
            result = self.middleware.blocked_ips()

            # Verify cache was called
            mock_cache.assert_called_once()
            self.assertIsInstance(result, set)

    def test_invalid_ip_address(self):
        """Test that the middleware handles invalid IP addresses gracefully."""
        request = self._create_mock_request(ip="invalid-ip", user_agent="NormalBrowser")

        # Call the middleware - should not crash
        response = self.middleware(request)

        # Request should be allowed (invalid IP is not in blocked list)
        self.assertEqual(response.status_code, 200)

    def test_empty_user_agent(self):
        """Test that the middleware handles empty user agents."""
        request = self._create_mock_request(ip="1.2.3.4", user_agent="")

        # Call the middleware
        response = self.middleware(request)

        # Request should be allowed
        self.assertEqual(response.status_code, 200)

    def test_no_ip_address(self):
        """Test that the middleware handles requests without IP addresses."""
        request = MagicMock()
        request.META = {
            "REMOTE_ADDR": "",
            "HTTP_USER_AGENT": "Test",
            "HTTP_X_FORWARDED_FOR": "",
        }
        request.path = "/test/"

        # Call the middleware
        response = self.middleware(request)

        # Request should be allowed
        self.assertEqual(response.status_code, 200)

        # Verify no IP record was created
        ip_count = IP.objects.filter(path="/test/").count()
        self.assertEqual(ip_count, 0)
