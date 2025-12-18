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
