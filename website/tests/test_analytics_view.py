from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils import timezone

from website.models import Organization, UserActivity


class UserBehaviorAnalyticsTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user("testuser", "test@example.com", "password")
        self.org = Organization.objects.create(name="Test Org", url="https://test.com")

        # Create sample activities
        for i in range(10):
            UserActivity.objects.create(
                user=self.user,
                organization=self.org,
                activity_type="bug_report",
                timestamp=timezone.now() - timedelta(days=i),
            )

    def test_analytics_context_data(self):
        """Test that analytics data is correctly calculated"""
        from website.views.company import OrganizationDashboardAnalyticsView

        view = OrganizationDashboardAnalyticsView()
        analytics = view.get_user_behavior_analytics(self.org)

        # Verify analytics structure
        self.assertIn("active_users_count", analytics)
        self.assertIn("total_activities", analytics)
        self.assertIn("engagement_rate", analytics)
        self.assertIn("top_users", analytics)
        self.assertIn("activity_breakdown", analytics)
        self.assertIn("weekly_trend", analytics)

        # Verify data
        self.assertGreater(analytics["active_users_count"], 0)
        self.assertGreater(analytics["total_activities"], 0)
