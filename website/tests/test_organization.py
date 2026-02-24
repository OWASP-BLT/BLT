from concurrent.futures import TimeoutError as FuturesTimeoutError
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse
from django.utils.timezone import now

from website.models import DailyStatusReport, Domain, Issue, Organization
from website.views.company import OrganizationDashboardCyberView
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


class OrganizationSwitcherTests(TestCase):
    def setUp(self):
        # Create test user
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123", email="test@example.com")

        # Create first organization with user as admin
        self.org1 = Organization.objects.create(
            name="Organization 1",
            description="First org",
            slug="org-1",
            url="https://org1.example.com",
            admin=self.user,
        )

        # Create second organization with user as manager
        self.org2 = Organization.objects.create(
            name="Organization 2",
            description="Second org",
            slug="org-2",
            url="https://org2.example.com",
        )
        self.org2.managers.add(self.user)

    def test_organization_switcher_appears_with_multiple_orgs(self):
        """Test that organization switcher appears when user has multiple organizations"""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("organization_analytics", kwargs={"id": self.org1.id})
        response = self.client.get(url)

        # Check that organization switcher is present
        self.assertContains(response, "organization-switcher")
        # Check that both organizations are in the dropdown
        self.assertContains(response, self.org1.name)
        self.assertContains(response, self.org2.name)

    def test_organization_switcher_not_shown_with_single_org(self):
        """Test that organization switcher is not shown when user has only one organization"""
        # Create a new user with only one organization
        single_org_user = User.objects.create_user(
            username="singleorguser", password="testpass123", email="single@example.com"
        )
        single_org = Organization.objects.create(
            name="Single Organization",
            description="Only org",
            slug="single-org",
            url="https://single.example.com",
            admin=single_org_user,
        )

        self.client.login(username="singleorguser", password="testpass123")
        url = reverse("organization_analytics", kwargs={"id": single_org.id})
        response = self.client.get(url)

        # Switcher should not be present
        self.assertNotContains(response, "organization-switcher")
        # But organization name should still be shown
        self.assertContains(response, single_org.name)

    def test_organization_context_in_all_dashboard_views(self):
        """Test that organizations context is passed to all dashboard views"""
        self.client.login(username="testuser", password="testpass123")

        # Test analytics view
        url = reverse("organization_analytics", kwargs={"id": self.org1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("organizations", response.context)

        # Test team overview view
        url = reverse("organization_team_overview", kwargs={"id": self.org1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("organizations", response.context)

        # Test bugs view
        url = reverse("organization_manage_bugs", kwargs={"id": self.org1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("organizations", response.context)

        # Test roles view
        url = reverse("organization_manage_roles", kwargs={"id": self.org1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("organizations", response.context)

        # Test cyber view
        url = reverse("organization_cyber", kwargs={"id": self.org1.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("organizations", response.context)


class OrganizationCyberDashboardTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username="cyberadmin", password="testpass123", email="cyberadmin@example.com"
        )
        self.manager_user = User.objects.create_user(
            username="cybermanager", password="testpass123", email="cybermanager@example.com"
        )
        self.outsider_user = User.objects.create_user(
            username="cyberoutsider", password="testpass123", email="cyberoutsider@example.com"
        )

        self.organization = Organization.objects.create(
            name="Cyber Org",
            description="Org for cyber dashboard tests",
            slug="cyber-org",
            url="https://cyber.example.com",
            admin=self.admin_user,
        )
        self.organization.managers.add(self.manager_user)

    def tearDown(self):
        cache.clear()

    @patch("website.views.company.get_domain_dns_posture")
    def test_admin_and_manager_can_access_cyber_dashboard(self, mock_dns_posture):
        mock_dns_posture.return_value = {"domain": "example.com", "spf": True, "dmarc": True, "dnssec": True}
        Domain.objects.create(
            name="example.com", url="https://example.com", organization=self.organization, is_active=True
        )

        self.client.login(username="cyberadmin", password="testpass123")
        admin_response = self.client.get(reverse("organization_cyber", kwargs={"id": self.organization.id}))
        self.assertEqual(admin_response.status_code, 200)
        self.assertContains(admin_response, "Cyber Dashboard")

        self.client.logout()
        self.client.login(username="cybermanager", password="testpass123")
        manager_response = self.client.get(reverse("organization_cyber", kwargs={"id": self.organization.id}))
        self.assertEqual(manager_response.status_code, 200)
        self.assertContains(manager_response, "Cyber Dashboard")

    def test_outsider_cannot_access_cyber_dashboard(self):
        self.client.login(username="cyberoutsider", password="testpass123")
        response = self.client.get(reverse("organization_cyber", kwargs={"id": self.organization.id}))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")

    @patch("website.views.company.get_domain_dns_posture")
    def test_dns_metrics_are_rendered(self, mock_dns_posture):
        Domain.objects.create(
            name="good.example", url="https://good.example", organization=self.organization, is_active=True
        )
        Domain.objects.create(
            name="bad.example", url="https://bad.example", organization=self.organization, is_active=True
        )
        mock_dns_posture.side_effect = [
            {"domain": "good.example", "spf": True, "dmarc": True, "dnssec": True},
            {"domain": "bad.example", "spf": False, "dmarc": True, "dnssec": False},
        ]

        self.client.login(username="cyberadmin", password="testpass123")
        response = self.client.get(reverse("organization_cyber", kwargs={"id": self.organization.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "good.example")
        self.assertContains(response, "bad.example")
        self.assertContains(response, "DNS Compliance")
        self.assertContains(response, "Pass")
        self.assertContains(response, "Fail")

    @patch("website.views.company.get_domain_dns_posture")
    def test_empty_state_when_no_domains(self, mock_dns_posture):
        self.client.login(username="cyberadmin", password="testpass123")
        response = self.client.get(reverse("organization_cyber", kwargs={"id": self.organization.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No active domains to evaluate yet.")
        self.assertContains(response, "No active domains found. Add a domain to start DNS checks.")
        mock_dns_posture.assert_not_called()

    @patch("website.views.company.get_domain_dns_posture")
    def test_dns_results_are_cached(self, mock_dns_posture):
        Domain.objects.create(
            name="cache.example", url="https://cache.example", organization=self.organization, is_active=True
        )
        mock_dns_posture.return_value = {"domain": "cache.example", "spf": True, "dmarc": True, "dnssec": True}

        self.client.login(username="cyberadmin", password="testpass123")
        url = reverse("organization_cyber", kwargs={"id": self.organization.id})

        first_response = self.client.get(url)
        second_response = self.client.get(url)

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(mock_dns_posture.call_count, 1)

    @patch("website.views.company.get_domain_dns_posture")
    def test_cache_invalidates_after_domain_update(self, mock_dns_posture):
        domain = Domain.objects.create(
            name="stale.example",
            url="https://stale.example",
            organization=self.organization,
            is_active=True,
        )
        mock_dns_posture.return_value = {"domain": "stale.example", "spf": True, "dmarc": True, "dnssec": True}

        self.client.login(username="cyberadmin", password="testpass123")
        url = reverse("organization_cyber", kwargs={"id": self.organization.id})

        first_response = self.client.get(url)
        self.assertEqual(first_response.status_code, 200)
        self.assertContains(first_response, "stale.example")

        domain.is_active = False
        domain.save(update_fields=["is_active"])

        second_response = self.client.get(url)
        self.assertEqual(second_response.status_code, 200)
        self.assertContains(second_response, "No active domains to evaluate yet.")

    @patch("website.views.company.as_completed")
    @patch("website.views.company.ThreadPoolExecutor")
    def test_timeout_uses_non_blocking_executor_shutdown(self, mock_executor_class, mock_as_completed):
        Domain.objects.create(
            name="timeout.example", url="https://timeout.example", organization=self.organization, is_active=True
        )
        fake_future = MagicMock()
        fake_executor = MagicMock()
        fake_executor.submit.return_value = fake_future
        mock_executor_class.return_value = fake_executor
        mock_as_completed.side_effect = FuturesTimeoutError()

        view = OrganizationDashboardCyberView()
        metrics = view._build_dns_metrics(self.organization.id)

        self.assertEqual(metrics["total_domains"], 1)
        self.assertEqual(metrics["compliant_count"], 0)
        fake_future.cancel.assert_called_once()
        fake_executor.shutdown.assert_called_once_with(wait=False, cancel_futures=True)


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
