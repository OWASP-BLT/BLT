from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import RequestFactory, TestCase

from website.middleware import ActivityTrackingMiddleware
from website.models import Organization, UserActivity


class ActivityMiddlewareTest(TestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()
        self.user = User.objects.create_user("testuser", "test@example.com", "password")
        self.org = Organization.objects.create(name="Test Org", url="https://test.com")
        self.middleware = ActivityTrackingMiddleware(get_response=lambda r: None)

    def test_dashboard_visit_tracked(self):
        """Test that dashboard visits are tracked"""
        initial_count = UserActivity.objects.count()

        request = self.factory.get(f"/organization/{self.org.id}/dashboard/")
        request.user = self.user
        request.session = {}

        self.middleware(request)

        # Check activity was created
        self.assertEqual(UserActivity.objects.count(), initial_count + 1)

        activity = UserActivity.objects.latest("timestamp")
        self.assertEqual(activity.activity_type, "dashboard_visit")
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.organization, self.org)
        self.assertIn("path", activity.metadata)
        self.assertEqual(activity.metadata["path"], f"/organization/{self.org.id}/dashboard/")

    def test_non_dashboard_not_tracked(self):
        """Test that non-dashboard pages are not tracked"""
        initial_count = UserActivity.objects.count()

        request = self.factory.get("/some-other-page/")
        request.user = self.user
        request.session = {}

        self.middleware(request)

        # No activity should be created
        self.assertEqual(UserActivity.objects.count(), initial_count)

    def test_superuser_dashboard_not_tracked(self):
        """Test that superuser dashboard visits are not tracked"""
        initial_count = UserActivity.objects.count()

        superuser = User.objects.create_superuser("admin", "admin@example.com", "password")
        request = self.factory.get(f"/organization/{self.org.id}/dashboard/")
        request.user = superuser
        request.session = {}

        self.middleware(request)

        # No activity should be created for superusers
        self.assertEqual(UserActivity.objects.count(), initial_count)

    def test_duplicate_dashboard_visit_within_minute_not_tracked(self):
        """Test that duplicate dashboard visits within 1 minute are deduplicated using cache"""
        from django.core.cache import cache

        # Clear cache before test
        cache.clear()

        initial_count = UserActivity.objects.count()

        # First visit
        request1 = self.factory.get(f"/organization/{self.org.id}/dashboard/")
        request1.user = self.user
        request1.session = {}

        self.middleware(request1)

        # Verify first visit was tracked
        self.assertEqual(UserActivity.objects.count(), initial_count + 1)

        # Check that cache key was set
        cache_key = f"dashboard_visit:{self.user.id}:{self.org.id}:/organization/{self.org.id}/dashboard/"
        self.assertTrue(cache.get(cache_key))

        # Second visit within 1 minute (should be deduplicated via cache)
        request2 = self.factory.get(f"/organization/{self.org.id}/dashboard/")
        request2.user = self.user
        request2.session = {}

        self.middleware(request2)

        # Verify no new activity was created (still only 1)
        self.assertEqual(UserActivity.objects.count(), initial_count + 1)

    def test_dashboard_visit_after_minute_is_tracked(self):
        """Test that dashboard visits after cache expiry are tracked separately"""
        from datetime import timedelta

        from django.core.cache import cache
        from django.utils import timezone

        cache.clear()
        initial_count = UserActivity.objects.count()

        # First visit
        request1 = self.factory.get(f"/organization/{self.org.id}/dashboard/")
        request1.user = self.user
        request1.session = {}
        self.middleware(request1)

        self.assertEqual(UserActivity.objects.count(), initial_count + 1)

        # ✅ Simulate that the first visit happened > 1 minute ago (DB dedupe should NOT match now)
        first = UserActivity.objects.latest("timestamp")
        first.timestamp = timezone.now() - timedelta(minutes=2)
        first.save(update_fields=["timestamp"])

        # Clear cache key (simulating cache expiry)
        cache_key = f"dashboard_visit:{self.user.id}:{self.org.id}:/organization/{self.org.id}/dashboard/"
        cache.delete(cache_key)

        # Second visit (should now be tracked)
        request2 = self.factory.get(f"/organization/{self.org.id}/dashboard/")
        request2.user = self.user
        request2.session = {}
        self.middleware(request2)

        self.assertEqual(UserActivity.objects.count(), initial_count + 2)

    def test_cache_key_includes_organization_and_path(self):
        """Test that cache key differentiates between different organizations and paths"""
        from django.core.cache import cache

        # Clear cache before test
        cache.clear()

        # Create second organization
        org2 = Organization.objects.create(name="Test Org 2", url="https://testorg2.com")

        initial_count = UserActivity.objects.count()

        # Visit org1 dashboard
        request1 = self.factory.get(f"/organization/{self.org.id}/dashboard/")
        request1.user = self.user
        request1.session = {}

        self.middleware(request1)

        # Visit org2 dashboard (different org, should create new activity)
        request2 = self.factory.get(f"/organization/{org2.id}/dashboard/")
        request2.user = self.user
        request2.session = {}

        self.middleware(request2)

        # Both visits should be tracked (different cache keys due to different orgs)
        self.assertEqual(UserActivity.objects.count(), initial_count + 2)

    def test_ip_address_is_anonymized(self):
        """Test that IP addresses are anonymized before storage"""
        cache.clear()
        request = self.factory.get(f"/organization/{self.org.id}/dashboard/")
        request.user = self.user
        request.session = {}
        request.META["REMOTE_ADDR"] = "192.168.1.100"

        self.middleware(request)

        activity = UserActivity.objects.latest("timestamp")
        # Last octet should be masked to 0
        self.assertEqual(activity.ip_address, "192.168.1.0")
