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
            name="Test Organization", description="Test Description", slug="test-org", url="https://test-org.com"
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


class OrganizationSocialRedirectViewTests(TestCase):
    """Tests for the OrganizationSocialRedirectView - social media click tracking"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123", email="test@example.com")

        self.organization = Organization.objects.create(
            name="Test Org",
            slug="test-org",
            url="https://testorg.com",
            twitter="https://twitter.com/testorg",
            facebook="https://facebook.com/testorg",
            linkedin="https://linkedin.com/company/testorg",
            github_org="testorg",
            social_clicks={},
        )

    def test_valid_twitter_redirect_increments_counter(self):
        """Test that clicking Twitter link redirects and increments counter"""
        url = reverse("organization_social_redirect", kwargs={"org_id": self.organization.id, "platform": "twitter"})
        response = self.client.get(url)

        # Should redirect
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.organization.twitter)

        # Check click was tracked
        self.organization.refresh_from_db()
        self.assertEqual(self.organization.social_clicks.get("twitter", 0), 1)

    def test_valid_linkedin_redirect_increments_counter(self):
        """Test that clicking LinkedIn link redirects and increments counter"""
        url = reverse("organization_social_redirect", kwargs={"org_id": self.organization.id, "platform": "linkedin"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.organization.linkedin)

        self.organization.refresh_from_db()
        self.assertEqual(self.organization.social_clicks.get("linkedin", 0), 1)

    def test_valid_facebook_redirect_increments_counter(self):
        """Test that clicking Facebook link redirects and increments counter"""
        url = reverse("organization_social_redirect", kwargs={"org_id": self.organization.id, "platform": "facebook"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.organization.facebook)

        self.organization.refresh_from_db()
        self.assertEqual(self.organization.social_clicks.get("facebook", 0), 1)

    def test_valid_github_redirect_constructs_url(self):
        """Test that clicking GitHub link constructs URL from github_org and redirects"""
        url = reverse("organization_social_redirect", kwargs={"org_id": self.organization.id, "platform": "github"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"https://github.com/{self.organization.github_org}")

        self.organization.refresh_from_db()
        self.assertEqual(self.organization.social_clicks.get("github", 0), 1)

    def test_multiple_clicks_increment_counter(self):
        """Test that multiple clicks increment the counter correctly"""
        url = reverse("organization_social_redirect", kwargs={"org_id": self.organization.id, "platform": "twitter"})

        # Click 3 times
        for i in range(3):
            self.client.get(url)

        self.organization.refresh_from_db()
        self.assertEqual(self.organization.social_clicks.get("twitter", 0), 3)

    def test_invalid_platform_returns_400(self):
        """Test that invalid platform returns bad request"""
        url = reverse("organization_social_redirect", kwargs={"org_id": self.organization.id, "platform": "invalid"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

    def test_nonexistent_organization_returns_404(self):
        """Test that non-existent organization returns 404"""
        url = reverse("organization_social_redirect", kwargs={"org_id": 99999, "platform": "twitter"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_prevents_open_redirect_attack_twitter(self):
        """Test that malicious Twitter URLs are blocked"""
        org = Organization.objects.create(
            name="Evil Org",
            slug="evil-org",
            url="https://evil-org.com",
            twitter="https://evil.com/phishing",
            social_clicks={},
        )

        url = reverse("organization_social_redirect", kwargs={"org_id": org.id, "platform": "twitter"})
        response = self.client.get(url)

        # Should redirect to dashboard with error, not to evil.com
        self.assertEqual(response.status_code, 302)
        self.assertIn(f"/organization/{org.id}/dashboard/analytics/", response.url)

    def test_prevents_open_redirect_attack_x_domain(self):
        """Test that x.com domain is allowed for twitter"""
        org = Organization.objects.create(
            name="X Org", slug="x-org", url="https://x-org.com", twitter="https://x.com/testorg", social_clicks={}
        )

        url = reverse("organization_social_redirect", kwargs={"org_id": org.id, "platform": "twitter"})
        response = self.client.get(url)

        # x.com should be allowed
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://x.com/testorg")

    def test_prevents_open_redirect_attack_subdomain(self):
        """Test that subdomains of allowed domains work"""
        org = Organization.objects.create(
            name="Subdomain Org",
            slug="subdomain-org",
            url="https://subdomain-org.com",
            linkedin="https://www.linkedin.com/company/testorg",
            social_clicks={},
        )

        url = reverse("organization_social_redirect", kwargs={"org_id": org.id, "platform": "linkedin"})
        response = self.client.get(url)

        # Subdomain should be allowed
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "https://www.linkedin.com/company/testorg")

    def test_missing_social_url_shows_error(self):
        """Test that missing social URL shows error message"""
        org = Organization.objects.create(
            name="No Social Org", slug="no-social", url="https://no-social.com", linkedin=None, social_clicks={}
        )

        url = reverse("organization_social_redirect", kwargs={"org_id": org.id, "platform": "linkedin"})
        response = self.client.get(url)

        # Should redirect back to dashboard
        self.assertEqual(response.status_code, 302)
        self.assertIn(f"/organization/{org.id}/dashboard/analytics/", response.url)

    def test_missing_github_org_shows_error(self):
        """Test that missing github_org field shows error"""
        org = Organization.objects.create(
            name="No GitHub Org", slug="no-github", url="https://no-github.com", github_org=None, social_clicks={}
        )

        url = reverse("organization_social_redirect", kwargs={"org_id": org.id, "platform": "github"})
        response = self.client.get(url)

        # Should redirect back to dashboard
        self.assertEqual(response.status_code, 302)
        self.assertIn(f"/organization/{org.id}/dashboard/analytics/", response.url)


class OrganizationProfileEditViewTests(TestCase):
    """Tests for the OrganizationProfileEditView - profile editing functionality"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123", email="test@example.com")
        self.organization = Organization.objects.create(
            name="Test Org",
            slug="test-org",
            url="https://test-org-profile.com",
            admin=self.user,
            description="Test description",
        )
        self.client.login(username="testuser", password="testpass123")

    def test_edit_profile_page_loads(self):
        """Test that edit profile page loads correctly"""
        url = reverse("organization_profile_edit", kwargs={"id": self.organization.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Org")
        self.assertIn("form", response.context)

    def test_edit_profile_requires_authentication(self):
        """Test that unauthenticated users cannot access edit page"""
        self.client.logout()
        url = reverse("organization_profile_edit", kwargs={"id": self.organization.id})
        response = self.client.get(url)

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_update_profile_with_valid_data(self):
        """Test updating organization profile with valid data"""
        url = reverse("organization_profile_edit", kwargs={"id": self.organization.id})
        data = {
            "name": "Updated Org Name",
            "url": "https://updated-org.com",
            "description": "New description",
            "twitter": "https://twitter.com/newhandle",
            "linkedin": "https://linkedin.com/company/neworg",
            "github_org": "neworg",
        }

        response = self.client.post(url, data)

        # Should redirect to analytics
        self.assertEqual(response.status_code, 302)
        self.assertIn("/dashboard/analytics/", response.url)

        # Verify data was saved
        self.organization.refresh_from_db()
        self.assertEqual(self.organization.name, "Updated Org Name")
        self.assertEqual(self.organization.url, "https://updated-org.com")
        self.assertEqual(self.organization.description, "New description")
        self.assertEqual(self.organization.twitter, "https://twitter.com/newhandle")
        self.assertEqual(self.organization.linkedin, "https://linkedin.com/company/neworg")
        self.assertEqual(self.organization.github_org, "neworg")

    def test_update_profile_with_invalid_url(self):
        """Test that invalid URLs are rejected"""
        url = reverse("organization_profile_edit", kwargs={"id": self.organization.id})
        data = {"name": "Test Org", "url": "https://testorg.com", "twitter": "not-a-valid-url"}

        response = self.client.post(url, data)

        # Should not redirect (form errors)
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        self.assertTrue(response.context["form"].errors)

    def test_manager_can_edit_organization(self):
        """Test that organization managers can edit the profile"""
        manager = User.objects.create_user(username="manager", password="managerpass", email="manager@example.com")
        self.organization.managers.add(manager)

        self.client.logout()
        self.client.login(username="manager", password="managerpass")

        url = reverse("organization_profile_edit", kwargs={"id": self.organization.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

    def test_non_member_cannot_edit_organization(self):
        """Test that non-members cannot edit the organization"""
        User.objects.create_user(username="other", password="otherpass", email="other@example.com")

        self.client.logout()
        self.client.login(username="other", password="otherpass")

        url = reverse("organization_profile_edit", kwargs={"id": self.organization.id})
        response = self.client.get(url)

        # Should be forbidden or redirect
        self.assertIn(response.status_code, [302, 403])


class OrganizationSocialStatsTests(TestCase):
    """Tests for the get_social_stats method in OrganizationDashboardAnalyticsView"""

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123", email="test@example.com")

        self.organization = Organization.objects.create(
            name="Test Org",
            slug="test-org",
            url="https://test-org-stats.com",
            admin=self.user,
            twitter="https://twitter.com/testorg",
            facebook="https://facebook.com/testorg",
            linkedin="https://linkedin.com/company/testorg",
            github_org="testorg",
            social_clicks={"twitter": 10, "facebook": 5, "linkedin": 3, "github": 8},
        )
        self.client.login(username="testuser", password="testpass123")

    def test_get_social_stats_returns_correct_data(self):
        """Test that social stats are correctly returned"""
        url = reverse("organization_analytics", kwargs={"id": self.organization.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertIn("social_stats", response.context)

        social_stats = response.context["social_stats"]

        # Check has_* flags
        self.assertTrue(social_stats["has_twitter"])
        self.assertTrue(social_stats["has_facebook"])
        self.assertTrue(social_stats["has_linkedin"])
        self.assertTrue(social_stats["has_github"])

        # Check click counts
        self.assertEqual(social_stats["twitter_clicks"], 10)
        self.assertEqual(social_stats["facebook_clicks"], 5)
        self.assertEqual(social_stats["linkedin_clicks"], 3)
        self.assertEqual(social_stats["github_clicks"], 8)

    def test_get_social_stats_with_no_social_links(self):
        """Test that stats show False for organizations without social links"""
        org = Organization.objects.create(
            name="No Social Org", slug="no-social", url="https://no-social-org.com", admin=self.user, social_clicks={}
        )

        url = reverse("organization_analytics", kwargs={"id": org.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        social_stats = response.context["social_stats"]

        # All should be False
        self.assertFalse(social_stats["has_twitter"])
        self.assertFalse(social_stats["has_facebook"])
        self.assertFalse(social_stats["has_linkedin"])
        self.assertFalse(social_stats["has_github"])

        # All clicks should be 0
        self.assertEqual(social_stats["twitter_clicks"], 0)
        self.assertEqual(social_stats["facebook_clicks"], 0)
        self.assertEqual(social_stats["linkedin_clicks"], 0)
        self.assertEqual(social_stats["github_clicks"], 0)

    def test_get_social_stats_with_empty_social_clicks(self):
        """Test that stats handle empty social_clicks dict correctly"""
        org = Organization.objects.create(
            name="Empty Clicks Org",
            slug="empty-clicks",
            url="https://empty-clicks-org.com",
            admin=self.user,
            twitter="https://twitter.com/test",
            social_clicks={},
        )

        url = reverse("organization_analytics", kwargs={"id": org.id})
        response = self.client.get(url)

        social_stats = response.context["social_stats"]

        # Has twitter but no clicks yet
        self.assertTrue(social_stats["has_twitter"])
        self.assertEqual(social_stats["twitter_clicks"], 0)
