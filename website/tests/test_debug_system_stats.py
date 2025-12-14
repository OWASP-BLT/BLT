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
    """Test debug panel API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

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

    @override_settings(DEBUG=True, TESTING=False)
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
    def test_run_migrations_requires_superuser(self):
        """Test that running migrations requires superuser privileges"""
        self.reload_urls()
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse("api_debug_run_migrations"), {"confirm": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        data = response.json()
        self.assertFalse(data["success"])

    @override_settings(DEBUG=True)
    def test_run_migrations_requires_confirm_flag(self):
        """Test that migrations require an explicit confirm flag"""
        self.reload_urls()
        self.user.is_superuser = True
        self.user.save()
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("api_debug_run_migrations"), {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        data = response.json()
        self.assertFalse(data["success"])

    @override_settings(DEBUG=True)
    def test_run_migrations_success_for_superuser(self):
        """Test that a superuser can run migrations with confirmation"""
        self.reload_urls()
        self.user.is_superuser = True
        self.user.save()
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("api_debug_run_migrations"), {"confirm": True}, format="json")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    @override_settings(DEBUG=True)
    @patch("website.api.views.call_command")
    def test_run_migrations_handles_errors(self, mock_call_command):
        """Test that migration errors are handled gracefully"""
        self.reload_urls()
        mock_call_command.side_effect = Exception("Migration failed")
        self.user.is_superuser = True
        self.user.save()
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("api_debug_run_migrations"), {"confirm": True}, format="json")

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        data = response.json()
        self.assertFalse(data["success"])

    @override_settings(DEBUG=True)
    def test_collect_static_requires_superuser(self):
        """Test that collectstatic endpoint requires superuser privileges"""
        self.reload_urls()
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("api_debug_collect_static"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        data = response.json()
        self.assertFalse(data["success"])

    @override_settings(DEBUG=True)
    def test_collect_static_success_for_superuser(self):
        """Test that a superuser can call collectstatic successfully"""
        self.reload_urls()
        self.user.is_superuser = True
        self.user.save()
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("api_debug_collect_static"))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    @override_settings(DEBUG=True)
    @patch("website.api.views.call_command")
    def test_collect_static_handles_errors(self, mock_call_command):
        """Test that collectstatic errors are handled gracefully"""
        self.reload_urls()
        mock_call_command.side_effect = Exception("Collectstatic failed")

        self.user.is_superuser = True
        self.user.save()
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("api_debug_collect_static"))

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
    def test_post_endpoints_require_authentication(self):
        """Test that POST debug endpoints require authentication when in debug mode"""
        self.reload_urls()
        post_endpoints = [
            "api_debug_clear_cache",
            "api_debug_populate_data",
            "api_debug_run_migrations",
            "api_debug_collect_static",
        ]

        for endpoint in post_endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.post(reverse(endpoint))
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    @override_settings(DEBUG=False)
    def test_all_endpoints_require_debug_mode(self):
        """Test that all debug endpoints are blocked in production"""
        self.reload_urls()
        endpoints = [
            "api_debug_system_stats",
            "api_debug_cache_info",
            "api_debug_panel_status",
            "api_debug_clear_cache",
            "api_debug_populate_data",
            "api_debug_run_migrations",
            "api_debug_collect_static",
        ]

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                with self.assertRaises(NoReverseMatch):
                    reverse(endpoint)

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
    def test_debug_endpoint_requires_authentication(self):
        """Test that debug endpoints require authentication even locally"""
        self.reload_urls()
        # Don't authenticate
        response = self.client.get(reverse("api_debug_system_stats"), HTTP_HOST="localhost:8000")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
