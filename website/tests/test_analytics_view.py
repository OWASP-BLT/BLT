from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils import timezone

from website.models import Organization, UserActivity
from website.views.company import OrganizationDashboardAnalyticsView

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
    
    def test_analytics_with_zero_activities(self):
        """Test analytics gracefully handles organizations with no activities"""

        # Create a new organization with no activities
        empty_org = Organization.objects.create(name="Empty Org", url="https://empty.com")
        
        view = OrganizationDashboardAnalyticsView()
        analytics = view.get_user_behavior_analytics(empty_org)

        # Verify structure still exists
        self.assertIn("active_users_count", analytics)
        self.assertIn("total_activities", analytics)
        self.assertIn("engagement_rate", analytics)
        self.assertIn("top_users", analytics)
        self.assertIn("activity_breakdown", analytics)
        self.assertIn("weekly_trend", analytics)

        # Verify zero values
        self.assertEqual(analytics["active_users_count"], 0)
        self.assertEqual(analytics["total_activities"], 0)
        self.assertEqual(analytics["engagement_rate"], 0)  # Tests division by zero protection
        self.assertEqual(len(analytics["top_users"]), 0)
        self.assertEqual(len(analytics["activity_breakdown"]), 0)
        self.assertEqual(len(analytics["weekly_trend"]), 0)
