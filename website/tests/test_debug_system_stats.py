from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


class DebugPanelAPITest(TestCase):
    """Test debug panel API endpoints"""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

    @override_settings(DEBUG=True)
    def test_get_system_stats_success(self):
        """Test getting system stats in debug mode"""
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
        """Test that system stats endpoint is forbidden in production"""
        response = self.client.get(reverse("api_debug_system_stats"))
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data["success"])

    @override_settings(DEBUG=True)
    def test_get_cache_info_success(self):
        """Test getting cache information"""
        response = self.client.get(reverse("api_debug_cache_info"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("backend", data["data"])
        self.assertIn("keys_count", data["data"])

    @override_settings(DEBUG=True)
    def test_clear_cache_success(self):
        """Test clearing cache"""
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse("api_debug_clear_cache"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["message"], "Cache cleared successfully")

    @override_settings(DEBUG=False)
    def test_clear_cache_forbidden_in_production(self):
        """Test that cache clear is forbidden in production"""
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse("api_debug_clear_cache"))
        self.assertEqual(response.status_code, 403)

    @override_settings(DEBUG=True)
    def test_populate_data_success(self):
        """Test populating test data"""
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse("api_debug_populate_data"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    @override_settings(DEBUG=True)
    def test_populate_data_missing_fixture_returns_404(self):
        """Test that missing fixture file returns 404 and error payload"""
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
        mock_cache_clear.side_effect = Exception("Cache clear failed")
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("api_debug_clear_cache"))

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        data = response.json()
        self.assertFalse(data["success"])

    @override_settings(DEBUG=True)
    def test_run_migrations_requires_superuser(self):
        """Test that running migrations requires superuser privileges"""
        self.client.force_authenticate(self.user)
        response = self.client.post(reverse("api_debug_run_migrations"), {"confirm": True}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        data = response.json()
        self.assertFalse(data["success"])

    @override_settings(DEBUG=True)
    def test_run_migrations_requires_confirm_flag(self):
        """Test that migrations require an explicit confirm flag"""
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
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("api_debug_collect_static"))

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        data = response.json()
        self.assertFalse(data["success"])

    @override_settings(DEBUG=True)
    def test_collect_static_success_for_superuser(self):
        """Test that a superuser can call collectstatic successfully"""
        self.user.is_superuser = True
        self.user.save()
        self.client.force_authenticate(self.user)

        response = self.client.post(reverse("api_debug_collect_static"))

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])

    @override_settings(DEBUG=True)
    @patch("django.core.management.call_command")
    @patch("website.api.views.call_command")
    def test_collect_static_handles_errors(self, mock_views_call_command, mock_mgmt_call_command):
        """Test that collectstatic errors are handled gracefully"""
        # Ensure that whichever call_command reference the view uses will raise
        mock_views_call_command.side_effect = Exception("Collectstatic failed")
        mock_mgmt_call_command.side_effect = Exception("Collectstatic failed")

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
        response = self.client.get(reverse("api_debug_panel_status"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["data"]["debug_mode"])

    @override_settings(DEBUG=True)
    def test_post_endpoints_require_authentication(self):
        """Test that POST debug endpoints require authentication when in debug mode"""
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
        # GET endpoints - no auth needed
        endpoints = [
            "api_debug_system_stats",
            "api_debug_cache_info",
            "api_debug_panel_status",
        ]

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(reverse(endpoint))
                self.assertEqual(response.status_code, 403)

        # POST endpoints - authenticate user first, then test
        self.client.force_authenticate(self.user)
        post_endpoints = [
            "api_debug_clear_cache",
            "api_debug_populate_data",
            "api_debug_run_migrations",
            "api_debug_collect_static",
        ]

        for endpoint in post_endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.post(reverse(endpoint))
                self.assertEqual(response.status_code, 403)
