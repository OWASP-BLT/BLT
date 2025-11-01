from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from website.models import Domain, Issue, Organization


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


class RegisterOrganizationViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create multiple test organizations with is_active=True
        for i in range(7):
            Organization.objects.create(
                name=f"Test Organization {i}",
                url=f"https://example{i}.com",
                slug=f"test-org-{i}",
                is_active=True,
            )

    def test_register_organization_page_shows_last_5_organizations(self):
        """Test that the register organization page shows the last 5 registered organizations"""
        url = reverse("register_organization")
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)

        # Check that recent_organizations is in context and has exactly 5 items
        self.assertIn("recent_organizations", response.context)
        recent_orgs = response.context["recent_organizations"]
        self.assertEqual(len(recent_orgs), 5)

        # Check that organizations are ordered by creation date (newest first)
        for i in range(len(recent_orgs) - 1):
            self.assertGreaterEqual(recent_orgs[i].created, recent_orgs[i + 1].created)

        # Check that the most recent organizations are shown
        all_orgs = list(Organization.objects.filter(is_active=True).order_by("-created"))
        for i in range(5):
            self.assertEqual(recent_orgs[i].id, all_orgs[i].id)

    def test_register_organization_page_only_shows_active_organizations(self):
        """Test that only active organizations are shown"""
        # Create an inactive organization
        Organization.objects.create(
            name="Inactive Organization",
            url="https://inactive.com",
            slug="inactive-org",
            is_active=False,
        )

        url = reverse("register_organization")
        response = self.client.get(url)

        recent_orgs = response.context["recent_organizations"]

        # Verify none of the recent organizations are inactive
        for org in recent_orgs:
            self.assertTrue(org.is_active)
