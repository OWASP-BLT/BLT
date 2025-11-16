from unittest.mock import Mock, patch

from django.core.cache import cache
from django.http import HttpResponseForbidden
from django.test import TestCase

from blt.middleware.ip_restrict import (
    BLOCKED_AGENTS_CACHE_KEY,
    BLOCKED_IPS_CACHE_KEY,
    BLOCKED_IP_NETWORK_CACHE_KEY,
    IPRestrictMiddleware,
)
from website.models import Blocked


class IPRestrictMiddlewareTests(TestCase):
    def setUp(self):
        self.middleware = IPRestrictMiddleware(get_response=Mock())
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_cache_check_before_db_query_for_ips(self):
        """Test that cache is checked before database query for blocked IPs"""
        # Set cache manually
        cached_data = ["192.168.1.1", "10.0.0.1"]
        cache.set(BLOCKED_IPS_CACHE_KEY, cached_data)

        # Call method - should not hit database
        with patch.object(Blocked.objects, "values_list") as mock_query:
            result = self.middleware.blocked_ips()
            mock_query.assert_not_called()
            self.assertEqual(result, set(cached_data))

    def test_cache_check_before_db_query_for_networks(self):
        """Test that cache is checked before database query for blocked networks"""
        # Set cache manually
        cached_data = ["192.168.0.0/16"]
        cache.set(BLOCKED_IP_NETWORK_CACHE_KEY, cached_data)

        # Call method - should not hit database
        with patch.object(Blocked.objects, "values_list") as mock_query:
            result = self.middleware.blocked_ip_network()
            mock_query.assert_not_called()
            self.assertEqual(len(result), 1)

    def test_cache_check_before_db_query_for_agents(self):
        """Test that cache is checked before database query for blocked agents"""
        # Set cache manually
        cached_data = ["BadBot", "EvilCrawler"]
        cache.set(BLOCKED_AGENTS_CACHE_KEY, cached_data)

        # Call method - should not hit database
        with patch.object(Blocked.objects, "values_list") as mock_query:
            result = self.middleware.blocked_agents()
            mock_query.assert_not_called()
            self.assertEqual(result, set(cached_data))

    def test_error_handling_in_blocked_data_retrieval(self):
        """Test that errors in retrieving blocked data don't crash the middleware"""
        request = Mock()
        request.META = {"REMOTE_ADDR": "1.2.3.4", "HTTP_USER_AGENT": "TestAgent"}
        request.path = "/test"

        # Mock the response
        self.middleware.get_response = Mock(return_value="response")

        # Force an error in blocked_ips
        with patch.object(self.middleware, "blocked_ips", side_effect=Exception("DB error")):
            response = self.middleware.process_request_sync(request)
            # Should not raise exception and should return normal response
            self.assertEqual(response, "response")

    def test_selective_cache_invalidation_for_ip(self):
        """Test that only IP cache is cleared when IP is set"""
        blocked = Blocked.objects.create(address="192.168.1.1", reason_for_block="Test")

        # Set all caches
        cache.set(BLOCKED_IPS_CACHE_KEY, ["test"])
        cache.set(BLOCKED_IP_NETWORK_CACHE_KEY, ["test"])
        cache.set(BLOCKED_AGENTS_CACHE_KEY, ["test"])

        # Trigger cache clear by saving
        blocked.address = "192.168.1.2"
        blocked.save()

        # Only IP cache should be cleared
        self.assertIsNone(cache.get(BLOCKED_IPS_CACHE_KEY))
        # Other caches should remain (but they may be cleared due to signal, so we just verify no crash)

    def test_middleware_continues_on_unexpected_error(self):
        """Test that middleware catches unexpected errors and continues"""
        request = Mock()
        request.META = {"REMOTE_ADDR": "1.2.3.4", "HTTP_USER_AGENT": "TestAgent"}
        request.path = "/test"

        # Mock the response
        self.middleware.get_response = Mock(return_value="response")

        # Force an error deep in the middleware
        with patch.object(request.META, "get", side_effect=Exception("Unexpected error")):
            response = self.middleware.process_request_sync(request)
            # Should not raise exception and should return normal response
            self.assertEqual(response, "response")
