from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from website.models import Domain, Hunt, Issue, Organization


class IssueVerificationTests(TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.client = Client()

        # Create users
        self.org_admin = User.objects.create_user(
            username="orgadmin", password="testpass123", email="admin@example.com"
        )
        self.domain_manager = User.objects.create_user(
            username="manager", password="testpass123", email="manager@example.com"
        )
        self.regular_user = User.objects.create_user(
            username="regular", password="testpass123", email="regular@example.com"
        )
        self.issue_reporter = User.objects.create_user(
            username="reporter", password="testpass123", email="reporter@example.com"
        )

        # Create organization
        self.organization = Organization.objects.create(
            name="Test Organization",
            description="Test Description",
            slug="test-org",
            admin=self.org_admin,
        )

        # Create domain with manager
        self.domain = Domain.objects.create(
            name="example.com",
            url="https://example.com",
            organization=self.organization,
            email="contact@example.com",
        )
        self.domain.managers.add(self.domain_manager)

        # Create a regular issue (non-hunt)
        self.regular_issue = Issue.objects.create(
            user=self.issue_reporter,
            domain=self.domain,
            url="https://example.com/issue1",
            description="Test issue",
            status="open",
            verified=False,
        )

        # Create a hunt issue
        self.hunt = Hunt.objects.create(
            name="Test Hunt",
            domain=self.domain,
            url="https://example.com",
            description="Test Hunt Description",
        )
        self.hunt_issue = Issue.objects.create(
            user=self.issue_reporter,
            domain=self.domain,
            hunt=self.hunt,
            url="https://example.com/hunt-issue",
            description="Test hunt issue",
            status="open",
            verified=False,
        )

    def test_verify_issue_by_domain_manager(self):
        """Test that domain managers can verify issues"""
        self.client.login(username="manager", password="testpass123")

        url = reverse("verify_issue", kwargs={"issue_id": self.regular_issue.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["verified"])

        # Verify the issue was actually updated
        self.regular_issue.refresh_from_db()
        self.assertTrue(self.regular_issue.verified)

    def test_verify_issue_by_org_admin(self):
        """Test that organization admins can verify issues"""
        self.client.login(username="orgadmin", password="testpass123")

        url = reverse("verify_issue", kwargs={"issue_id": self.regular_issue.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertTrue(data["verified"])

        # Verify the issue was actually updated
        self.regular_issue.refresh_from_db()
        self.assertTrue(self.regular_issue.verified)

    def test_verify_issue_denied_for_regular_user(self):
        """Test that regular users cannot verify issues"""
        self.client.login(username="regular", password="testpass123")

        url = reverse("verify_issue", kwargs={"issue_id": self.regular_issue.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("permission", data["error"].lower())

        # Verify the issue was not updated
        self.regular_issue.refresh_from_db()
        self.assertFalse(self.regular_issue.verified)

    def test_verify_issue_requires_login(self):
        """Test that verification requires authentication"""
        url = reverse("verify_issue", kwargs={"issue_id": self.regular_issue.id})
        response = self.client.post(url)

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login", response.url)

    def test_verify_issue_toggle(self):
        """Test that verification can be toggled on and off"""
        self.client.login(username="manager", password="testpass123")

        url = reverse("verify_issue", kwargs={"issue_id": self.regular_issue.id})

        # First request should verify the issue
        response = self.client.post(url)
        data = response.json()
        self.assertTrue(data["verified"])

        # Second request should unverify the issue
        response = self.client.post(url)
        data = response.json()
        self.assertFalse(data["verified"])

        # Verify final state
        self.regular_issue.refresh_from_db()
        self.assertFalse(self.regular_issue.verified)

    def test_verify_issue_requires_post_method(self):
        """Test that verification only accepts POST requests"""
        self.client.login(username="manager", password="testpass123")

        url = reverse("verify_issue", kwargs={"issue_id": self.regular_issue.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 405)
        data = response.json()
        self.assertFalse(data["success"])

    def test_accept_bug_permission_check_for_domain_manager(self):
        """Test that accept_bug enforces permission checks for domain managers"""
        self.client.login(username="manager", password="testpass123")

        url = reverse("accept_bug", kwargs={"issue_id": self.hunt_issue.id, "reward_id": "no_reward"})
        response = self.client.get(url)

        # Should redirect to the bughunt page (success)
        self.assertEqual(response.status_code, 302)

        # Verify the issue was verified
        self.hunt_issue.refresh_from_db()
        self.assertTrue(self.hunt_issue.verified)

    def test_accept_bug_permission_denied_for_regular_user(self):
        """Test that accept_bug denies access to regular users"""
        self.client.login(username="regular", password="testpass123")

        url = reverse("accept_bug", kwargs={"issue_id": self.hunt_issue.id, "reward_id": "no_reward"})
        response = self.client.get(url)

        # Should redirect with error message
        self.assertEqual(response.status_code, 302)

        # Verify the issue was not verified
        self.hunt_issue.refresh_from_db()
        self.assertFalse(self.hunt_issue.verified)

    def test_issue_view_context_contains_is_domain_manager_flag(self):
        """Test that IssueView provides is_domain_manager flag to template"""
        self.client.login(username="manager", password="testpass123")

        url = reverse("issue_view", kwargs={"slug": self.regular_issue.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["is_domain_manager"])

    def test_issue_view_context_is_domain_manager_false_for_regular_user(self):
        """Test that is_domain_manager is False for regular users"""
        self.client.login(username="regular", password="testpass123")

        url = reverse("issue_view", kwargs={"slug": self.regular_issue.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["is_domain_manager"])
