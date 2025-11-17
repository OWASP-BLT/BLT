from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from website.models import Domain, Issue, Organization
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
