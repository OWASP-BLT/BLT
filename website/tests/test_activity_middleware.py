from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from website.middleware import ActivityTrackingMiddleware
from website.models import Organization, UserActivity


class ActivityMiddlewareTest(TestCase):
    def setUp(self):
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
        """Test that duplicate dashboard visits within 1 minute are deduplicated"""

        initial_count = UserActivity.objects.count()

        # First visit
        request1 = self.factory.get(f"/organization/{self.org.id}/dashboard/")
        request1.user = self.user
        request1.session = {}

        self.middleware(request1)

        # Verify first visit was tracked
        self.assertEqual(UserActivity.objects.count(), initial_count + 1)

        # Second visit within 1 minute (should be deduplicated)
        request2 = self.factory.get(f"/organization/{self.org.id}/dashboard/")
        request2.user = self.user
        request2.session = {}

        self.middleware(request2)

        # Verify no new activity was created (still only 1)
        self.assertEqual(UserActivity.objects.count(), initial_count + 1)

    def test_dashboard_visit_after_minute_is_tracked(self):
        """Test that dashboard visits after 1 minute are tracked separately"""
        from datetime import timedelta
        from unittest.mock import patch

        from django.utils import timezone

        initial_count = UserActivity.objects.count()

        # First visit
        request1 = self.factory.get(f"/organization/{self.org.id}/dashboard/")
        request1.user = self.user
        request1.session = {}

        # Mock timezone to set first visit timestamp
        base_time = timezone.now()
        with patch("website.middleware.timezone.now", return_value=base_time):
            self.middleware(request1)

        # Verify first visit was tracked
        self.assertEqual(UserActivity.objects.count(), initial_count + 1)

        # Manually update the first activity's timestamp to be 2 minutes ago
        first_activity = UserActivity.objects.latest("timestamp")
        first_activity.timestamp = base_time - timedelta(minutes=2)
        first_activity.save()

        # Second visit (now more than 1 minute later)
        request2 = self.factory.get(f"/organization/{self.org.id}/dashboard/")
        request2.user = self.user
        request2.session = {}

        self.middleware(request2)

        # Verify new activity was created (now 2 activities)
        self.assertEqual(UserActivity.objects.count(), initial_count + 2)
