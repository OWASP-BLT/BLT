# tests/test_throttling.py
import os
import sys

import django
from django.core.cache import cache
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

# Add the project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blt.settings")
django.setup()

from rest_framework.response import Response
from rest_framework.views import APIView

from blt.middleware.throttling import ThrottlingMiddleware


# Mock DRF View (should NOT be throttled)
class MockDRFView(APIView):
    def get(self, request):
        return Response({"data": "DRF response"})


# Mock Regular Django View (should BE throttled)
def regular_django_view(request):
    return HttpResponse("Regular Django response")


class ThrottlingTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.final_response = HttpResponse("Final response", status=200)
        self.middleware = ThrottlingMiddleware(lambda r: self.final_response)
        self.regular_request = self.factory.get("/regular-view/")

        self.drf_request = self.factory.get("/api/test/")
        self.drf_request.resolver_match = type("resolver", (), {"func": MockDRFView.as_view()})
        cache.clear()  # Reset cache before each test

    def test_get_request_throttling(self):
        """Test that GET requests are throttled after limit is exceeded."""
        ip = "192.168.1.1"
        # Make 100 requests (should all be allowed)
        for i in range(100):
            request = self.factory.get("/some-path", REMOTE_ADDR=ip)
            response = self.middleware(request)
            # self.assertIsNone(response, f"Request {i+1} should be allowed")
            self.assertEqual(response.status_code, 200, "Request {i+1} should be allowed")

        # 101st request should be throttled
        request = self.factory.get("/some-path", REMOTE_ADDR=ip)
        response = self.middleware(request)
        self.assertEqual(response.status_code, 429, "101st request should be throttled")

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
        exempt_paths = ["/admin/", "/static/", "/media/"]

        for path in exempt_paths:
            # Make many requests to exempt path
            for i in range(200):
                request = self.factory.get(path, REMOTE_ADDR=ip)
                response = self.middleware(request)
                self.assertEqual(response.status_code, 200, f"Exempt path {path} request {i+1} should be allowed")


if __name__ == "__main__":
    import unittest

    unittest.main()
