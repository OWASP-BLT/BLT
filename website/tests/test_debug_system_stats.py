from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient


class DebugPanelAPITest(TestCase):
    """Test debug panel API endpoints"""

    def setUp(self):
        self.client = APIClient()

    @override_settings(DEBUG=True)
    def test_get_system_stats_success(self):
        """Test getting system stats in debug mode"""
        response = self.client.get(reverse('api_debug_system_stats'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('python_version', data['data'])
        self.assertIn('django_version', data['data'])
        self.assertIn('memory', data['data'])
        self.assertIn('disk', data['data'])

    @override_settings(DEBUG=False)
    def test_system_stats_forbidden_in_production(self):
        """Test that system stats endpoint is forbidden in production"""
        response = self.client.get(reverse('api_debug_system_stats'))
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])

    @override_settings(DEBUG=True)
    def test_get_cache_info_success(self):
        """Test getting cache information"""
        response = self.client.get(reverse('api_debug_cache_info'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('backend', data['data'])
        self.assertIn('keys_count', data['data'])

    @override_settings(DEBUG=True)
    def test_clear_cache_success(self):
        """Test clearing cache"""
        response = self.client.post(reverse('api_debug_clear_cache'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Cache cleared successfully')

    @override_settings(DEBUG=False)
    def test_clear_cache_forbidden_in_production(self):
        """Test that cache clear is forbidden in production"""
        response = self.client.post(reverse('api_debug_clear_cache'))
        self.assertEqual(response.status_code, 403)

    @override_settings(DEBUG=True)
    def test_populate_data_success(self):
        """Test populating test data"""
        response = self.client.post(reverse('api_debug_populate_data'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])

    @override_settings(DEBUG=True)
    def test_get_debug_panel_status(self):
        """Test getting debug panel status"""
        response = self.client.get(reverse('api_debug_panel_status'))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(data['data']['debug_mode'])

    @override_settings(DEBUG=False)
    def test_all_endpoints_require_debug_mode(self):
        """Test that all debug endpoints are blocked in production"""
        endpoints = [
            'api_debug_system_stats',
            'api_debug_cache_info',
            'api_debug_panel_status',
        ]
        
        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(reverse(endpoint))
                self.assertEqual(response.status_code, 403)
        
        post_endpoints = [
            'api_debug_clear_cache',
            'api_debug_populate_data',
            'api_debug_run_migrations',
            'api_debug_collect_static',
        ]
        
        for endpoint in post_endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.post(reverse(endpoint))
                self.assertEqual(response.status_code, 403)
