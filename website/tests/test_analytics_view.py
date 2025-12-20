from datetime import timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.utils import timezone
from django.urls import reverse
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

    def _attach_user_to_org(self):
        # FK-style ownership fields
        for fk_name in ("owner", "created_by", "creator", "user", "admin"):
            try:
                field = self.org._meta.get_field(fk_name)
            except Exception:
                continue
            if getattr(field, "many_to_one", False) or getattr(field, "one_to_one", False):
                setattr(self.org, fk_name, self.user)
                self.org.save()
                return

        # M2M membership fields
        for m2m_name in ("members", "users", "admins", "owners"):
            if hasattr(self.org, m2m_name):
                try:
                    getattr(self.org, m2m_name).add(self.user)
                    return
                except Exception:
                    pass

    def test_analytics_context_data(self):
        """Test that analytics data is correctly calculated"""

        view = OrganizationDashboardAnalyticsView()
        analytics = view.get_user_behavior_analytics(self.org)

        # Verify analytics structure
        self.assertIn("active_users_count", analytics)
        self.assertIn("total_activities", analytics)
        self.assertIn("engagement_rate", analytics)
        self.assertIn("top_users", analytics)
        self.assertIn("activity_breakdown", analytics)
        self.assertIn("weekly_trend", analytics)
        self.assertIn("peak_hours", analytics)

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
        self.assertEqual(len(analytics["peak_hours"]), 0)

    def test_analytics_view_integration(self):
        self.client.force_login(self.user)

        # 1) Make sure user is actually associated with org
        self._attach_user_to_org()

        # 2) Select org in session (common keys used in projects)
        session = self.client.session
        session["org_ref"] = self.org.id
        session["org_id"] = self.org.id
        session["organization_id"] = self.org.id
        session["selected_organization_id"] = self.org.id
        session.save()

        # 3) Seed at least one activity so analytics context is definitely built
        UserActivity.objects.create(
            user=self.user,
            organization=self.org,
            activity_type="dashboard_visit",
            timestamp=timezone.now(),
            metadata={"path": "/organization/dashboard/"},
        )

        # 4) Hit dashboard URL and follow redirects
        url = f"/organization/{self.org.id}/dashboard/analytics/"
        response = self.client.get(url, follow=True)

        self.assertEqual(response.request["PATH_INFO"], url)
        self.assertEqual(response.status_code, 200)

        # Analytics context must exist
        self.assertIn("user_behavior", response.context)

        # Template should actually show analytics section
        self.assertContains(response, "User Behavior Analytics")