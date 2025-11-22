from datetime import date
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from django.utils.timezone import now

from website.models import DailyStatusReport, Domain, Issue, Organization
from website.views.organization import BountyPayoutsView


class DomainViewTests(TestCase):
    def setUp(self):
        # Create test user
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123", email="test@example.com")

        # Create test organization
        self.organization = Organization.objects.create(
            name="Test Organization", description="Test Description", slug="test-org"
        )

        # Create test domain
        self.domain = Domain.objects.create(
            name="example.com",
            url="https://example.com",
            organization=self.organization,
            email="contact@example.com",
            clicks=42,
        )

        # Create some test issues for the domain
        self.open_issue = Issue.objects.create(
            user=self.user,
            domain=self.domain,
            url="https://example.com/issue1",
            description="Test open issue",
            status="open",
        )

        self.closed_issue = Issue.objects.create(
            user=self.user,
            domain=self.domain,
            url="https://example.com/issue2",
            description="Test closed issue",
            status="closed",
        )

    def test_public_domain_view(self):
        """Test the public domain view"""
        url = reverse("domain", kwargs={"slug": self.domain.name})
        response = self.client.get(url)

        # Check basic domain info is displayed
        self.assertContains(response, self.domain.name)
        self.assertContains(response, self.domain.url)
        self.assertContains(response, self.organization.name)

        # Check issues are displayed
        self.assertContains(response, self.open_issue.description)
        self.assertContains(response, self.closed_issue.description)


class OrganizationCheckInTests(TestCase):
    def setUp(self):
        # Create test client
        self.client = Client()

        # Create test users
        self.admin_user = User.objects.create_user(username="admin", password="admin123", email="admin@example.com")
        self.manager_user = User.objects.create_user(
            username="manager", password="manager123", email="manager@example.com"
        )
        self.regular_user = User.objects.create_user(username="user", password="user123", email="user@example.com")

        # Create test organization with check-ins enabled
        self.organization = Organization.objects.create(
            name="Test Org",
            description="Test Description",
            slug="test-org",
            url="https://testorg.com",
            check_ins_enabled=True,
            admin=self.admin_user,
        )
        self.organization.managers.add(self.manager_user)

        # Create some test check-ins
        self.checkin1 = DailyStatusReport.objects.create(
            user=self.regular_user,
            organization=self.organization,
            date=date.today(),
            previous_work="Worked on feature X",
            next_plan="Will work on feature Y",
            blockers="No blockers",
            goal_accomplished=True,
            current_mood="Happy 😊",
        )

        self.checkin2 = DailyStatusReport.objects.create(
            user=self.manager_user,
            organization=self.organization,
            date=date.today(),
            previous_work="Reviewed PRs",
            next_plan="Will plan sprint",
            blockers="Waiting for approval",
            goal_accomplished=False,
            current_mood="Neutral 😐",
        )

    def test_organization_checkins_access_admin(self):
        """Test that admin can access organization check-ins"""
        self.client.login(username="admin", password="admin123")
        url = reverse("organization_checkins", kwargs={"slug": self.organization.slug})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Check-In Reports")
        self.assertContains(response, self.checkin1.previous_work[:15])
        self.assertContains(response, self.checkin2.previous_work[:15])

    def test_organization_checkins_access_manager(self):
        """Test that manager can access organization check-ins"""
        self.client.login(username="manager", password="manager123")
        url = reverse("organization_checkins", kwargs={"slug": self.organization.slug})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Check-In Reports")

    def test_organization_checkins_access_denied_regular_user(self):
        """Test that regular user cannot access organization check-ins"""
        self.client.login(username="user", password="user123")
        url = reverse("organization_checkins", kwargs={"slug": self.organization.slug})
        response = self.client.get(url)

        # Should redirect with permission error
        self.assertEqual(response.status_code, 302)

    def test_organization_checkins_disabled(self):
        """Test that check-ins page redirects when check-ins are disabled"""
        # Disable check-ins
        self.organization.check_ins_enabled = False
        self.organization.save()

        self.client.login(username="admin", password="admin123")
        url = reverse("organization_checkins", kwargs={"slug": self.organization.slug})
        response = self.client.get(url)

        # Should redirect with warning
        self.assertEqual(response.status_code, 302)

    def test_add_checkin_with_organization(self):
        """Test adding a check-in with organization"""
        self.client.login(username="user", password="user123")

        response = self.client.post(
            reverse("sizzle_daily_log"),
            {
                "previous_work": "Completed testing",
                "next_plan": "Start new feature",
                "blockers": "None",
                "goal_accomplished": "on",
                "feeling": "Great 🎉",
                "organization_url": self.organization.url,
            },
        )

        self.assertEqual(response.status_code, 200)

        # Verify check-in was created with organization
        latest_checkin = DailyStatusReport.objects.filter(user=self.regular_user).latest("created")
        self.assertEqual(latest_checkin.organization, self.organization)
        self.assertEqual(latest_checkin.previous_work, "Completed testing")

    def test_add_checkin_without_organization(self):
        """Test adding a check-in without organization (optional field)"""
        self.client.login(username="user", password="user123")

        response = self.client.post(
            reverse("sizzle_daily_log"),
            {
                "previous_work": "Personal work",
                "next_plan": "Continue learning",
                "blockers": "None",
                "goal_accomplished": "on",
                "feeling": "Good 👍",
            },
        )

        self.assertEqual(response.status_code, 200)

        # Verify check-in was created without organization
        latest_checkin = DailyStatusReport.objects.filter(user=self.regular_user).latest("created")
        self.assertIsNone(latest_checkin.organization)
        self.assertEqual(latest_checkin.previous_work, "Personal work")
class BountyPayoutsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123", email="test@example.com")
        self.user.is_staff = True
        self.user.save()
        self.view = BountyPayoutsView()

    def tearDown(self):
        # Clear cache after each test
        cache.clear()

    @patch("website.views.organization.requests.get")
    def test_github_issues_with_bounties_returns_tuple(self, mock_get):
        """Test that github_issues_with_bounties always returns a tuple of (issues, total_count)"""
        # Mock the GitHub API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": [{"id": 1, "title": "Test Issue"}], "total_count": 1}
        mock_get.return_value = mock_response

        # First call should fetch from API and cache the result
        result = self.view.github_issues_with_bounties("$5", "closed", 1, 100)
        self.assertIsInstance(result, tuple, "Result should be a tuple")
        self.assertEqual(len(result), 2, "Result should have 2 elements")
        issues, total_count = result
        self.assertEqual(len(issues), 1)
        self.assertEqual(total_count, 1)

        # Second call should return cached data (still a tuple)
        result_cached = self.view.github_issues_with_bounties("$5", "closed", 1, 100)
        self.assertIsInstance(result_cached, tuple, "Cached result should be a tuple")
        self.assertEqual(len(result_cached), 2, "Cached result should have 2 elements")
        issues_cached, total_count_cached = result_cached
        self.assertEqual(len(issues_cached), 1)
        self.assertEqual(total_count_cached, 1)

    @patch("website.views.organization.requests.get")
    def test_github_issues_with_bounties_error_returns_tuple(self, mock_get):
        """Test that github_issues_with_bounties returns empty tuple on error"""
        # Mock an API error
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        # Should return empty tuple
        result = self.view.github_issues_with_bounties("$5", "closed", 1, 100)
        self.assertIsInstance(result, tuple, "Error result should be a tuple")
        self.assertEqual(len(result), 2, "Error result should have 2 elements")
        issues, total_count = result
        self.assertEqual(len(issues), 0)
        self.assertEqual(total_count, 0)


class SizzleCheckInViewTests(TestCase):
    def setUp(self):
        # Create test user
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123", email="test@example.com")
        self.client.login(username="testuser", password="testpass123")

    def test_add_sizzle_checkin_view_loads(self):
        """Test that the add sizzle check-in view loads correctly"""
        response = self.client.get(reverse("add_sizzle_checkin"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "What did you work on previously?")

    def test_fill_from_previous_button_appears_with_yesterday_report(self):
        """Test that the Fill from Previous Check-in button appears when yesterday's report exists"""
        # Create yesterday's report
        yesterday = now().date() - timedelta(days=1)
        DailyStatusReport.objects.create(
            user=self.user,
            date=yesterday,
            previous_work="Previous work from yesterday",
            next_plan="This should be filled in today's previous work",
            blockers="No blockers",
        )

        response = self.client.get(reverse("add_sizzle_checkin"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Fill from Previous Check-in")
        self.assertContains(response, "fillFromPreviousBtn")

    def test_fill_from_previous_button_not_shown_without_yesterday_report(self):
        """Test that the Fill from Previous Check-in button is not shown when no yesterday report exists"""
        response = self.client.get(reverse("add_sizzle_checkin"))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Fill from Previous Check-in")
