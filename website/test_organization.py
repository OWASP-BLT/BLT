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

