# tests/test_throttling.py

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


if __name__ == "__main__":
    import unittest

    unittest.main()
