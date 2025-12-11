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

    def test_fill_from_previous_button_not_shown_without_any_checkins(self):
        """Test that no Fill button is shown when there are no check-ins at all"""
        response = self.client.get(reverse("add_sizzle_checkin"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No previous check-ins available")
        self.assertNotContains(response, "fillFromLastCheckinBtn")
        self.assertNotContains(response, "fillFromPreviousBtn")

    def test_fill_from_last_checkin_shown_without_yesterday_report(self):
        """Test that Fill from Last Check-in button appears when no yesterday report but has older check-in"""
        # Create a check-in from 3 days ago
        three_days_ago = now().date() - timedelta(days=3)
        DailyStatusReport.objects.create(
            user=self.user,
            date=three_days_ago,
            previous_work="Previous work from 3 days ago",
            next_plan="This should be filled in today's previous work",
            blockers="No blockers",
        )

        response = self.client.get(reverse("add_sizzle_checkin"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No report available for yesterday")
        self.assertContains(response, "Last check-in was on")
        self.assertContains(response, "Fill from Last Check-in")
        self.assertContains(response, "fillFromLastCheckinBtn")


class OrganizationSwitchingTests(TestCase):
    """Test organization switching functionality for administrators"""

    def setUp(self):
        self.client = Client()

        # Create users
        self.admin_user = User.objects.create_user(
            username="admin", password="adminpass123", email="admin@example.com", is_active=True
        )
        self.manager_user = User.objects.create_user(
            username="manager", password="managerpass123", email="manager@example.com", is_active=True
        )
        self.regular_user = User.objects.create_user(
            username="regular", password="regularpass123", email="regular@example.com", is_active=True
        )
        self.superuser = User.objects.create_user(
            username="superuser", password="superpass123", email="super@example.com", is_active=True, is_superuser=True
        )

        # Create organizations
        self.org1 = Organization.objects.create(
            name="Organization 1", description="First org", slug="org-1", url="https://org1.com", admin=self.admin_user
        )
        self.org2 = Organization.objects.create(
            name="Organization 2", description="Second org", slug="org-2", url="https://org2.com", admin=self.admin_user
        )
        self.org3 = Organization.objects.create(
            name="Organization 3", description="Third org", slug="org-3", url="https://org3.com"
        )

        # Add manager relationship
        self.org3.managers.add(self.manager_user)

    def test_admin_can_access_their_organizations(self):
        """Test that admin can access organizations they administer"""
        self.client.login(username="admin", password="adminpass123")
        response = self.client.get(reverse("admin_organization_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Organization 1")
        self.assertContains(response, "Organization 2")
        self.assertNotContains(response, "Organization 3")

    def test_manager_can_access_managed_organizations(self):
        """Test that manager can access organizations they manage"""
        self.client.login(username="manager", password="managerpass123")
        response = self.client.get(reverse("admin_organization_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Organization 3")
        self.assertNotContains(response, "Organization 1")
        self.assertNotContains(response, "Organization 2")

    def test_superuser_can_access_all_organizations(self):
        """Test that superuser can access all organizations"""
        self.client.login(username="superuser", password="superpass123")
        response = self.client.get(reverse("admin_organization_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Organization 1")
        self.assertContains(response, "Organization 2")
        self.assertContains(response, "Organization 3")

    def test_regular_user_cannot_access_dashboard(self):
        """Test that regular user without organizations is redirected"""
        self.client.login(username="regular", password="regularpass123")
        response = self.client.get(reverse("admin_organization_dashboard"))

        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertEqual(response.url, "/")

    def test_organization_switching_updates_session(self):
        """Test that switching organizations updates the session"""
        self.client.login(username="admin", password="adminpass123")

        # Switch to org2
        response = self.client.get(reverse("admin_organization_dashboard"), {"switch_to": self.org2.pk})

        self.assertEqual(response.status_code, 302)  # Redirect after switching
        self.assertEqual(self.client.session.get("selected_organization_id"), self.org2.pk)

    def test_organization_switcher_shown_for_multiple_orgs(self):
        """Test that organization switcher is shown when user manages multiple organizations"""
        self.client.login(username="admin", password="adminpass123")
        response = self.client.get(reverse("admin_organization_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Switch Organization")
        self.assertTrue(response.context["user_can_manage_multiple"])

    def test_organization_switcher_not_shown_for_single_org(self):
        """Test that organization switcher is not shown when user manages only one organization"""
        self.client.login(username="manager", password="managerpass123")
        response = self.client.get(reverse("admin_organization_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Switch Organization")
        self.assertFalse(response.context["user_can_manage_multiple"])

    def test_selected_organization_persists_in_session(self):
        """Test that selected organization persists across requests"""
        self.client.login(username="admin", password="adminpass123")

        # First request - should select org1 (first org)
        response = self.client.get(reverse("admin_organization_dashboard"))
        first_selected = response.context["selected_organization"]

        # Switch to org2
        self.client.get(reverse("admin_organization_dashboard"), {"switch_to": self.org2.pk})

        # Next request should maintain org2 selection
        response = self.client.get(reverse("admin_organization_dashboard"))
        self.assertEqual(response.context["selected_organization"].pk, self.org2.pk)

    def test_admin_can_view_organization_detail(self):
        """Test that admin can view details of their organization"""
        self.client.login(username="admin", password="adminpass123")
        response = self.client.get(reverse("admin_organization_dashboard_detail", kwargs={"pk": self.org1.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Organization 1")

    def test_admin_cannot_view_other_organization_detail(self):
        """Test that admin cannot view details of organization they don't manage"""
        self.client.login(username="admin", password="adminpass123")
        response = self.client.get(reverse("admin_organization_dashboard_detail", kwargs={"pk": self.org3.pk}))

        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertEqual(response.url, "/")

    def test_manager_can_view_managed_organization_detail(self):
        """Test that manager can view details of organization they manage"""
        self.client.login(username="manager", password="managerpass123")
        response = self.client.get(reverse("admin_organization_dashboard_detail", kwargs={"pk": self.org3.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Organization 3")

    def test_invalid_organization_switch_shows_error(self):
        """Test that switching to invalid organization shows error"""
        self.client.login(username="admin", password="adminpass123")

        # Try to switch to org3 which admin doesn't manage
        response = self.client.get(reverse("admin_organization_dashboard"), {"switch_to": self.org3.pk}, follow=True)

        # Should get error message
        messages = list(response.context["messages"])
        self.assertTrue(any("Invalid organization" in str(m) for m in messages))
