from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.test import RequestFactory, TestCase

from blt.middleware.ip_restrict import BLOCKED_AGENTS_CACHE_KEY, MAX_COUNT, IPRestrictMiddleware
from website.models import Blocked, IP


class IPRestrictMiddlewareTestCase(TestCase):
    """Test cases for IPRestrictMiddleware"""

    def setUp(self):
        """Set up test fixtures"""
        self.factory = RequestFactory()
        self.middleware = IPRestrictMiddleware(get_response=lambda request: Mock(status_code=200))

        # Clear cache before each test
        cache.clear()

        # Create test user
        self.user = User.objects.create_user(username="testuser", password="testpass")

    def tearDown(self):
        """Clean up after tests"""
        cache.clear()
        Blocked.objects.all().delete()
        IP.objects.all().delete()

    def test_blocked_ip_address(self):
        """Test that a blocked IP address is forbidden"""
        # Create a blocked IP
        Blocked.objects.create(address="192.168.1.1", reason_for_block="Testing")

        # Create a request from that IP
        request = self.factory.get("/test/")
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        # Process the request
        response = self.middleware(request)

        # Verify the response is forbidden
        self.assertIsInstance(response, HttpResponseForbidden)

        # Verify the block count was incremented
        blocked = Blocked.objects.get(address="192.168.1.1")
        self.assertEqual(blocked.count, 2)

    def test_blocked_ip_network(self):
        """Test that an IP in a blocked network is forbidden"""
        # Create a blocked network
        Blocked.objects.create(ip_network="192.168.1.0", reason_for_block="Testing network")

        # Create a request from an IP in that network
        request = self.factory.get("/test/")
        request.META["REMOTE_ADDR"] = "192.168.1.50"

        # Process the request
        response = self.middleware(request)

        # Verify the response is forbidden
        self.assertIsInstance(response, HttpResponseForbidden)

        # Verify the block count was incremented
        blocked = Blocked.objects.get(ip_network="192.168.1.0")
        self.assertEqual(blocked.count, 2)

    def test_blocked_user_agent(self):
        """Test that a blocked user agent is forbidden"""
        # Create a blocked user agent
        Blocked.objects.create(user_agent_string="BadBot", reason_for_block="Testing bot")

        # Create a request with that user agent
        request = self.factory.get("/test/")
        request.META["REMOTE_ADDR"] = "192.168.1.1"
        request.META["HTTP_USER_AGENT"] = "Mozilla/5.0 (compatible; BadBot/1.0)"

        # Process the request
        response = self.middleware(request)

        # Verify the response is forbidden
        self.assertIsInstance(response, HttpResponseForbidden)

        # Verify the block count was incremented
        blocked = Blocked.objects.get(user_agent_string="BadBot")
        self.assertEqual(blocked.count, 2)

    def test_allowed_ip_address(self):
        """Test that a non-blocked IP address is allowed"""
        # Create a request from a non-blocked IP
        request = self.factory.get("/test/")
        request.META["REMOTE_ADDR"] = "192.168.1.1"
        request.META["HTTP_USER_AGENT"] = "Mozilla/5.0"

        # Process the request
        response = self.middleware(request)

        # Verify the response is not forbidden
        self.assertNotIsInstance(response, HttpResponseForbidden)
        self.assertEqual(response.status_code, 200)

    def test_ip_tracking(self):
        """Test that IP access is tracked in the database"""
        # Create a request
        request = self.factory.get("/test-path/")
        request.META["REMOTE_ADDR"] = "192.168.1.100"
        request.META["HTTP_USER_AGENT"] = "Mozilla/5.0"

        # Process the request
        self.middleware(request)

        # Verify IP was recorded
        ip_record = IP.objects.filter(address="192.168.1.100", path="/test-path/").first()
        self.assertIsNotNone(ip_record)
        self.assertEqual(ip_record.count, 1)
        self.assertEqual(ip_record.agent, "Mozilla/5.0")

        # Process another request from same IP to same path
        self.middleware(request)

        # Verify count was incremented
        ip_record.refresh_from_db()
        self.assertEqual(ip_record.count, 2)

    def test_cache_blocked_ips(self):
        """Test that blocked IPs are cached"""
        # Create a blocked IP
        Blocked.objects.create(address="192.168.1.1", reason_for_block="Testing")

        # First call should hit database and cache the result
        blocked_ips = self.middleware.blocked_ips()
        self.assertIn("192.168.1.1", blocked_ips)

        # Verify cache was set
        cached_ips = cache.get("blocked_ips")
        self.assertIsNotNone(cached_ips)
        self.assertIn("192.168.1.1", cached_ips)

        # Create another blocked IP (won't be in cache)
        Blocked.objects.create(address="192.168.1.2", reason_for_block="Testing 2")

        # Second call should use cache (won't have the new IP)
        blocked_ips = self.middleware.blocked_ips()
        self.assertIn("192.168.1.1", blocked_ips)
        self.assertNotIn("192.168.1.2", blocked_ips)

    def test_cache_blocked_networks(self):
        """Test that blocked IP networks are cached"""
        # Create a blocked network
        Blocked.objects.create(ip_network="10.0.0.0", reason_for_block="Testing network")

        # First call should hit database and cache the result
        blocked_networks = self.middleware.blocked_ip_network()
        self.assertEqual(len(blocked_networks), 1)

        # Verify cache was set
        cached_networks = cache.get("blocked_ip_network")
        self.assertIsNotNone(cached_networks)

    def test_cache_blocked_agents(self):
        """Test that blocked user agents are cached"""
        # Create a blocked user agent
        Blocked.objects.create(user_agent_string="BadBot", reason_for_block="Testing bot")

        # First call should hit database and cache the result
        blocked_agents = self.middleware.blocked_agents()
        self.assertIn("BadBot", blocked_agents)

        # Verify cache was set
        cached_agents = cache.get(BLOCKED_AGENTS_CACHE_KEY)
        self.assertIsNotNone(cached_agents)
        self.assertIn("BadBot", cached_agents)

    def test_x_forwarded_for_header(self):
        """Test that X-Forwarded-For header is properly handled"""
        # Create a blocked IP
        Blocked.objects.create(address="192.168.1.1", reason_for_block="Testing")

        # Create a request with X-Forwarded-For header
        request = self.factory.get("/test/")
        request.META["HTTP_X_FORWARDED_FOR"] = "192.168.1.1, 10.0.0.1"
        request.META["REMOTE_ADDR"] = "10.0.0.1"

        # Process the request
        response = self.middleware(request)

        # Verify the response is forbidden (first IP in X-Forwarded-For is checked)
        self.assertIsInstance(response, HttpResponseForbidden)

    def test_invalid_ip_address_handling(self):
        """Test that invalid IP addresses are handled gracefully"""
        # Create a request with invalid IP
        request = self.factory.get("/test/")
        request.META["REMOTE_ADDR"] = "invalid-ip"
        request.META["HTTP_USER_AGENT"] = "Mozilla/5.0"

        # Process the request - should not raise exception
        response = self.middleware(request)

        # Verify the response is not forbidden
        self.assertNotIsInstance(response, HttpResponseForbidden)

    def test_invalid_ip_network_handling(self):
        """Test that invalid IP networks are handled gracefully"""
        # Create a blocked entry with invalid network
        Blocked.objects.create(ip_network="invalid-network", reason_for_block="Testing")

        # Call blocked_ip_network - should not raise exception
        blocked_networks = self.middleware.blocked_ip_network()

        # Verify empty list is returned (invalid network is skipped)
        self.assertEqual(len(blocked_networks), 0)

    def test_error_retrieving_blocked_data(self):
        """Test that errors retrieving blocked data don't break the middleware"""
        # Mock blocked_ips to raise an exception
        with patch.object(self.middleware, "blocked_ips", side_effect=Exception("Database error")):
            request = self.factory.get("/test/")
            request.META["REMOTE_ADDR"] = "192.168.1.1"

            # Process the request - should not raise exception
            response = self.middleware(request)

            # Verify the request is allowed through despite the error
            self.assertNotIsInstance(response, HttpResponseForbidden)
            self.assertEqual(response.status_code, 200)

    def test_user_agent_substring_matching(self):
        """Test that user agent blocking works with substring matching"""
        # Create a blocked user agent substring
        Blocked.objects.create(user_agent_string="BadBot", reason_for_block="Testing bot")

        # Test various user agents containing "BadBot"
        test_agents = [
            "Mozilla/5.0 (compatible; BadBot/1.0)",
            "BadBot",
            "Some-BadBot-Agent",
            "badbot",  # Should match case-insensitively
        ]

        for agent in test_agents:
            request = self.factory.get("/test/")
            request.META["REMOTE_ADDR"] = "192.168.1.1"
            request.META["HTTP_USER_AGENT"] = agent

            response = self.middleware(request)

            self.assertIsInstance(response, HttpResponseForbidden, f"User agent '{agent}' should be blocked")

    def test_none_values_filtered(self):
        """Test that None values are properly filtered out"""
        # Create blocked entries with None values
        Blocked.objects.create(address=None, user_agent_string="Bot1", reason_for_block="Test")
        Blocked.objects.create(address="192.168.1.1", user_agent_string=None, reason_for_block="Test")

        # Call methods that should filter out None values
        blocked_ips = self.middleware.blocked_ips()
        blocked_agents = self.middleware.blocked_agents()

        # Verify None values are not in results
        self.assertNotIn(None, blocked_ips)
        self.assertNotIn(None, blocked_agents)

    def test_ip_count_max_limit(self):
        """Test that IP count doesn't exceed MAX_COUNT"""
        # Create an IP record with count near max
        ip_record = IP.objects.create(address="192.168.1.1", agent="Mozilla/5.0", count=MAX_COUNT - 1, path="/test/")

        # Create a request from that IP
        request = self.factory.get("/test/")
        request.META["REMOTE_ADDR"] = "192.168.1.1"
        request.META["HTTP_USER_AGENT"] = "Mozilla/5.0"

        # Process the request
        self.middleware(request)

        # Verify count is at MAX_COUNT
        ip_record.refresh_from_db()
        self.assertEqual(ip_record.count, MAX_COUNT)

        # Process another request
        self.middleware(request)

        # Verify count stays at MAX_COUNT
        ip_record.refresh_from_db()
        self.assertEqual(ip_record.count, MAX_COUNT)

    def test_unexpected_middleware_error_handling(self):
        """Test that unexpected errors in middleware are caught and logged"""

        # Mock get_response to raise an exception during processing
        def mock_get_response(request):
            raise Exception("Unexpected error")

        middleware = IPRestrictMiddleware(get_response=mock_get_response)

        # Mock the process_request_sync to raise exception
        with patch.object(middleware, "process_request_sync", side_effect=Exception("Unexpected error")):
            request = self.factory.get("/test/")
            request.META["REMOTE_ADDR"] = "192.168.1.1"

            # Process the request - should catch exception and return response
            with patch("blt.middleware.ip_restrict.logger.error") as mock_logger:
                response = middleware(request)

                # Verify error was logged
                mock_logger.assert_called()

    def test_empty_ip_address(self):
        """Test handling of empty IP address"""
        # Create a request with empty IP
        request = self.factory.get("/test/")
        request.META["REMOTE_ADDR"] = ""
        request.META["HTTP_USER_AGENT"] = "Mozilla/5.0"

        # Process the request - should not raise exception
        response = self.middleware(request)

        # Verify the response is allowed through
        self.assertNotIsInstance(response, HttpResponseForbidden)

    def test_multiple_ips_same_path(self):
        """Test that multiple IPs can access the same path"""
        # Create requests from different IPs
        for i in range(1, 4):
            request = self.factory.get("/same-path/")
            request.META["REMOTE_ADDR"] = f"192.168.1.{i}"
            request.META["HTTP_USER_AGENT"] = "Mozilla/5.0"

            self.middleware(request)

        # Verify all IPs were recorded
        ip_records = IP.objects.filter(path="/same-path/")
        self.assertEqual(ip_records.count(), 3)

    def test_same_ip_different_paths(self):
        """Test that same IP accessing different paths is tracked separately"""
        # Create requests from same IP to different paths
        paths = ["/path1/", "/path2/", "/path3/"]
        for path in paths:
            request = self.factory.get(path)
            request.META["REMOTE_ADDR"] = "192.168.1.1"
            request.META["HTTP_USER_AGENT"] = "Mozilla/5.0"

            self.middleware(request)

        # Verify all paths were recorded separately
        for path in paths:
            ip_record = IP.objects.filter(address="192.168.1.1", path=path).first()
            self.assertIsNotNone(ip_record)
            self.assertEqual(ip_record.count, 1)
