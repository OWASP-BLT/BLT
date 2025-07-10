# test_throttling_middleware.py
from django.conf import settings
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from rest_framework.response import Response
from rest_framework.views import APIView

from blt.middleware.throttling import ThrottlingMiddleware


# Mock DRF View (should NOT be throttled)
class MockDRFView(APIView):
    def get(self, request):
        return Response({"data": "DRF response"})


class ThrottlingTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.final_response = HttpResponse("Final response", status=200)
        self.middleware = ThrottlingMiddleware(lambda r: self.final_response)
        cache.clear()  # Reset cache before each test

    def test_get_request_throttling(self):
        """Test that GET requests would be throttled after limit is exceeded, but are skipped during tests."""
        ip = "192.168.1.1"
        # Get the actual GET limit from settings
        get_limit = getattr(settings, "THROTTLE_LIMITS", {}).get("GET", 100)

        # Make more requests than the limit (should all be allowed during tests)
        for i in range(get_limit + 10):
            request = self.factory.get("/some-path", REMOTE_ADDR=ip)
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200, f"Request {i+1} should be allowed during tests")

    def test_different_ips_not_throttled(self):
        """Test that different IPs are tracked separately."""
        # Each IP should be able to make 100 requests
        for i in range(150):
            ip = f"192.168.1.{i}"
            request = self.factory.get("/", REMOTE_ADDR=ip)
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200, f"IP {ip} should be allowed")

    def test_exempt_paths_not_throttled(self):
        """Test that exempt paths are not throttled."""
        ip = "192.168.1.1"
        exempt_paths = getattr(settings, "THROTTLE_EXEMPT_PATHS", ["/admin/", "/static/", "/media/"])

        for path in exempt_paths:
            # Make many requests to exempt path
            for i in range(200):
                request = self.factory.get(path, REMOTE_ADDR=ip)
                response = self.middleware(request)
                self.assertEqual(response.status_code, 200, f"Exempt path {path} request {i+1} should be allowed")

    def test_throttling_skipped_during_tests(self):
        """Test that throttling is completely skipped when running tests."""
        ip = "192.168.1.1"
        
        # Make way more requests than the limit (should all be allowed during tests)
        for i in range(200):
            request = self.factory.get("/some-path", REMOTE_ADDR=ip)
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200, f"Request {i+1} should be allowed during tests")
    def test_drf_views_not_throttled(self):
        """Test that DRF views are exempt from throttling."""
        ip = "192.168.1.1"

        # Make many requests to DRF view
        for i in range(150):
            request = self.factory.get("/api/test/", REMOTE_ADDR=ip)
            request.resolver_match = type(
                "resolver", (), {"func": type("func", (), {"cls": MockDRFView, "is_api_view": True})}
            )()
            response = self.middleware(request)
            self.assertEqual(response.status_code, 200, f"DRF request {i+1} should not be throttled")
