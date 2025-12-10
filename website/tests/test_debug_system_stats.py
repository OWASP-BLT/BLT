from importlib import reload
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import NoReverseMatch, clear_url_caches, reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@override_settings(ALLOWED_HOSTS=["*"])
class DebugPanelAPITest(TestCase):
    """Tests for debug panel API endpoints"""

    def setUp(self):
        """Set up test fixtures"""
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.superuser = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="adminpass123"
        )

    def reload_urls(self):
        clear_url_caches()
        import blt.urls

        reload(blt.urls)

    @override_settings(DEBUG=True)
    def test_get_system_stats_success(self):
        """Test getting system stats in debug mode"""
        self.reload_urls()
        self.client.force_authenticate(self.user)
        response = self.client.get(reverse("api_debug_system_stats"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("python_version", data["data"])
        self.assertIn("django_version", data["data"])
        self.assertIn("memory", data["data"])
        self.assertIn("disk", data["data"])

    @override_settings(DEBUG=False)
    def test_system_stats_forbidden_in_production(self):
        """Debug URLs are not registered when DEBUG=False"""
        self.reload_urls()
        with self.assertRaises(NoReverseMatch):
            reverse("api_debug_system_stats")

    @override_settings(DEBUG=True)
    def test_get_cache_info_success(self):
        """Test getting cache information"""
        self.reload_urls()
        self.client.force_authenticate(self.user)
        response = self.client.get(reverse("api_debug_cache_info"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("backend", data["data"])
        self.assertIn("keys_count", data["data"])

    @override_settings(DEBUG=True)
    def test_clear_cache_success(self):
        """Test clearing cache"""
        self.reload_urls()
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse("api_debug_clear_cache"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["message"], "Cache cleared successfully")

    @override_settings(DEBUG=False)
    def test_clear_cache_forbidden_in_production(self):
        """Test that cache clear route is not registered in production"""
        self.reload_urls()
        with self.assertRaises(NoReverseMatch):
            reverse("api_debug_clear_cache")

    @override_settings(DEBUG=True)
    def test_populate_data_success(self):
        """Test populating test data"""
        self.reload_urls()
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse("api_debug_populate_data"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    @override_settings(DEBUG=True)
    def test_populate_data_missing_fixture_returns_404(self):
        """Test that missing fixture file returns 404 and error payload"""
        self.reload_urls()
        self.client.force_authenticate(self.user)

        with patch("website.api.views.os.path.exists", return_value=False):
            response = self.client.post(reverse("api_debug_populate_data"))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        data = response.json()
        self.assertFalse(data["success"])

    @override_settings(DEBUG=True)
    @patch("website.api.views.call_command")
    def test_populate_data_handles_errors(self, mock_call_command):
        """Test that errors while loading fixtures return 500 and error payload"""
        self.reload_urls()
        mock_call_command.side_effect = Exception("Fixture load failed")
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("api_debug_populate_data"))

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        data = response.json()
        self.assertFalse(data["success"])

    @override_settings(DEBUG=True)
    @patch("django.core.cache.cache.clear")
    def test_clear_cache_handles_errors(self, mock_cache_clear):
        """Test that cache clear endpoint handles errors gracefully"""
        self.reload_urls()
        mock_cache_clear.side_effect = Exception("Cache clear failed")
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("api_debug_clear_cache"))

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        data = response.json()
        self.assertFalse(data["success"])

    @override_settings(DEBUG=True)
    def test_get_debug_panel_status(self):
        """Test getting debug panel status"""
        self.reload_urls()
        self.client.force_authenticate(self.user)
        response = self.client.get(reverse("api_debug_panel_status"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["data"]["debug_mode"])

    @override_settings(DEBUG=True)
    def test_debug_endpoint_requires_authentication(self):
        """Test that debug endpoints require authentication even locally"""
        self.reload_urls()
        endpoints = [
            "api_debug_system_stats",
            "api_debug_cache_info",
            "api_debug_panel_status",
        ]

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(reverse(endpoint))
                self.assertEqual(
                    response.status_code,
                    status.HTTP_403_FORBIDDEN,
                    f"{endpoint} should return 403 for unauthenticated requests",
                )

    @override_settings(DEBUG=True)
    def test_post_endpoints_require_authentication(self):
        """Test that POST debug endpoints require authentication when in debug mode"""
        self.reload_urls()
        endpoints = [
            "api_debug_clear_cache",
            "api_debug_populate_data",
            "api_debug_sync_github",
        ]

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.post(reverse(endpoint))
                self.assertEqual(
                    response.status_code,
                    status.HTTP_403_FORBIDDEN,
                    f"{endpoint} should return 403 for unauthenticated POST requests",
                )

    @override_settings(DEBUG=True)
    def test_authenticated_user_can_access_debug_endpoints(self):
        """Test that authenticated users can access debug endpoints"""
        self.reload_urls()
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("api_debug_system_stats"))
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            "Authenticated user should access system stats endpoint",
        )

    @override_settings(DEBUG=True)
    def test_debug_endpoints_return_correct_data_structure(self):
        """Test that debug endpoints return data in expected format"""
        self.reload_urls()
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("api_debug_system_stats"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertIn("success", data)
        self.assertIn("data", data)
        self.assertTrue(data["success"])

        stats = data["data"]
        self.assertIn("memory", stats)
        self.assertIn("disk", stats)
        self.assertIn("python_version", stats)
        self.assertIn("django_version", stats)

    @override_settings(DEBUG=True)
    def test_cache_info_endpoint_returns_cache_stats(self):
        """Test that cache info endpoint returns cache statistics"""
        self.reload_urls()
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("api_debug_cache_info"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("backend", data["data"])
        self.assertIn("keys_count", data["data"])
        self.assertIn("hit_ratio", data["data"])

    @override_settings(DEBUG=True)
    def test_clear_cache_endpoint_clears_cache(self):
        """Test that clear cache endpoint works"""
        self.reload_urls()
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("api_debug_clear_cache"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        data = response.json()
        self.assertTrue(data["success"])

    @override_settings(DEBUG=True)
    def test_debug_endpoint_blocks_non_local_host(self):
        """Test that debug endpoints block access from non-local hosts even when DEBUG=True"""
        self.reload_urls()
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("api_debug_system_stats"), HTTP_HOST="example.com")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("local development", data["error"])

    @override_settings(DEBUG=True)
    def test_debug_endpoint_allows_localhost(self):
        """Test that debug endpoints allow localhost access"""
        self.reload_urls()
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("api_debug_system_stats"), HTTP_HOST="localhost:8000")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    @override_settings(DEBUG=True)
    def test_debug_endpoint_allows_127_0_0_1(self):
        """Test that debug endpoints allow 127.0.0.1 access"""
        self.reload_urls()
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("api_debug_system_stats"), HTTP_HOST="127.0.0.1:8000")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    @override_settings(DEBUG=True)
    def test_debug_endpoint_allows_127_prefix(self):
        """Test that debug endpoints allow 127.x.x.x IPs"""
        self.reload_urls()
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("api_debug_system_stats"), HTTP_HOST="127.0.1.1:8000")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    @override_settings(DEBUG=True)
    def test_debug_endpoint_allows_testserver(self):
        """Test that debug endpoints allow access from the Django test server"""
        self.reload_urls()
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("api_debug_system_stats"), HTTP_HOST="testserver")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    @override_settings(DEBUG=True)
    def test_debug_endpoint_blocks_external_ip(self):
        """Test that debug endpoints block access from external IPs"""
        self.reload_urls()
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("api_debug_system_stats"), HTTP_HOST="192.168.1.100:8000")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("local development", data["error"])

    @override_settings(DEBUG=True)
    def test_debug_endpoint_blocks_remote_host(self):
        """Test that debug endpoints block access from remote hosts"""
        self.reload_urls()
        self.client.force_authenticate(self.user)

        response = self.client.get(reverse("api_debug_system_stats"), HTTP_HOST="myapp.herokuapp.com")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        data = response.json()
        self.assertFalse(data["success"])

    @override_settings(DEBUG=True)
    @patch("website.api.views.call_command")
    def test_sync_github_data_success(self, mock_call_command):
        """Test that GitHub sync endpoint works"""
        self.reload_urls()
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("api_debug_sync_github"))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("details", data)

        # Verify management commands were called
        calls = [call[0][0] for call in mock_call_command.call_args_list]
        self.assertIn("check_owasp_projects", calls)

    @override_settings(DEBUG=True)
    def test_sync_github_data_requires_authentication(self):
        """Test that GitHub sync requires authentication"""
        self.reload_urls()

        response = self.client.post(reverse("api_debug_sync_github"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    @override_settings(DEBUG=True)
    @patch("website.api.views.call_command")
    def test_sync_github_data_handles_errors(self, mock_call_command):
        """Test GitHub sync error handling"""
        self.reload_urls()
        mock_call_command.side_effect = Exception("Sync failed")
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("api_debug_sync_github"))

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
