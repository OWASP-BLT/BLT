import hashlib
import hmac
import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from website.models import Organization, Project, Repo

User = get_user_model()


class ProjectWebhookTestCase(TestCase):
    """Test cases for project webhook functionality"""

    def setUp(self):
        """Set up test data"""
        # Create a test user
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

        # Create an organization
        self.org = Organization.objects.create(name="Test Organization", admin=self.user, url="https://example.com")

        # Create a project with webhook configured
        self.project = Project.objects.create(
            name="Test Project",
            slug="test-project",
            description="Test project description",
            organization=self.org,
            webhook_url="https://example.com/webhook",
            webhook_secret="test-secret-key",
        )

        # Create a project without webhook configured
        self.project_no_webhook = Project.objects.create(
            name="Project No Webhook",
            slug="project-no-webhook",
            description="Project without webhook",
            organization=self.org,
        )

        # Create test repositories
        self.repo1 = Repo.objects.create(
            name="Test Repo 1", slug="test-repo-1", repo_url="https://github.com/test/repo1", project=self.project
        )

        self.repo2 = Repo.objects.create(
            name="Test Repo 2", slug="test-repo-2", repo_url="https://github.com/test/repo2", project=self.project
        )

    def _generate_signature(self, secret, payload):
        """Helper method to generate HMAC signature"""
        return "sha256=" + hmac.new(secret.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def test_webhook_url_exists(self):
        """Test that webhook URL is accessible"""
        url = reverse("project_webhook", kwargs={"slug": self.project.slug})
        self.assertEqual(url, f"/project/{self.project.slug}/webhook/")

    def test_webhook_requires_post(self):
        """Test that webhook only accepts POST requests"""
        url = reverse("project_webhook", kwargs={"slug": self.project.slug})

        # Try GET request
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)  # Method Not Allowed

    def test_webhook_project_not_found(self):
        """Test webhook with non-existent project"""
        url = reverse("project_webhook", kwargs={"slug": "non-existent-project"})
        response = self.client.post(url, content_type="application/json")
        self.assertEqual(response.status_code, 404)

    def test_webhook_not_configured(self):
        """Test webhook with project that has no webhook configuration"""
        url = reverse("project_webhook", kwargs={"slug": self.project_no_webhook.slug})
        response = self.client.post(url, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertIn("not configured", data["message"])

    def test_webhook_missing_signature(self):
        """Test webhook without signature header"""
        url = reverse("project_webhook", kwargs={"slug": self.project.slug})
        response = self.client.post(url, content_type="application/json")
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertIn("Missing webhook signature", data["message"])

    def test_webhook_invalid_signature(self):
        """Test webhook with invalid signature"""
        url = reverse("project_webhook", kwargs={"slug": self.project.slug})
        payload = json.dumps({"event": "test"})

        # Use wrong signature
        response = self.client.post(
            url, data=payload, content_type="application/json", HTTP_X_WEBHOOK_SIGNATURE="sha256=invalid_signature"
        )
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertIn("Invalid webhook signature", data["message"])

    @patch("website.views.project.call_command")
    def test_webhook_valid_request(self, mock_call_command):
        """Test webhook with valid signature triggers stats recalculation"""
        url = reverse("project_webhook", kwargs={"slug": self.project.slug})
        payload = json.dumps({"event": "project_updated", "timestamp": "2024-01-01T00:00:00Z"})

        # Generate valid signature
        signature = self._generate_signature(self.project.webhook_secret, payload)

        # Make request with valid signature
        response = self.client.post(
            url, data=payload, content_type="application/json", HTTP_X_WEBHOOK_SIGNATURE=signature
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["project"], self.project.name)
        self.assertIn("repositories_updated", data)

        # Verify that update_contributor_stats was called for each repo
        self.assertEqual(mock_call_command.call_count, 2)
        mock_call_command.assert_any_call("update_contributor_stats", "--repo_id", self.repo1.id)
        mock_call_command.assert_any_call("update_contributor_stats", "--repo_id", self.repo2.id)

    @patch("website.views.project.call_command")
    def test_webhook_empty_payload(self, mock_call_command):
        """Test webhook with empty payload"""
        url = reverse("project_webhook", kwargs={"slug": self.project.slug})
        payload = ""

        # Generate valid signature for empty payload
        signature = self._generate_signature(self.project.webhook_secret, payload)

        # Make request with valid signature and empty payload
        response = self.client.post(
            url, data=payload, content_type="application/json", HTTP_X_WEBHOOK_SIGNATURE=signature
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")

        # Verify that update_contributor_stats was still called
        self.assertEqual(mock_call_command.call_count, 2)

    def test_webhook_project_no_repos(self):
        """Test webhook for project with no repositories"""
        # Create project without repos
        project_no_repos = Project.objects.create(
            name="Project No Repos",
            slug="project-no-repos",
            description="Project without repos",
            organization=self.org,
            webhook_url="https://example.com/webhook",
            webhook_secret="test-secret",
        )

        url = reverse("project_webhook", kwargs={"slug": project_no_repos.slug})
        payload = json.dumps({"event": "test"})
        signature = self._generate_signature(project_no_repos.webhook_secret, payload)

        response = self.client.post(
            url, data=payload, content_type="application/json", HTTP_X_WEBHOOK_SIGNATURE=signature
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("no repositories found", data["message"])

    @patch("website.views.project.call_command")
    def test_webhook_partial_failure(self, mock_call_command):
        """Test webhook when some repository updates fail"""
        url = reverse("project_webhook", kwargs={"slug": self.project.slug})
        payload = json.dumps({"event": "test"})
        signature = self._generate_signature(self.project.webhook_secret, payload)

        # Make the second call fail
        mock_call_command.side_effect = [None, Exception("Test error")]

        response = self.client.post(
            url, data=payload, content_type="application/json", HTTP_X_WEBHOOK_SIGNATURE=signature
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "partial_success")
        self.assertIn("errors", data)
        self.assertEqual(len(data["errors"]), 1)


class ProjectWebhookModelTestCase(TestCase):
    """Test cases for Project model webhook fields"""

    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

        self.org = Organization.objects.create(name="Test Organization", admin=self.user, url="https://example.com")

    def test_project_webhook_fields_optional(self):
        """Test that webhook fields are optional"""
        project = Project.objects.create(
            name="Test Project", slug="test-project", description="Test project description", organization=self.org
        )

        self.assertIsNone(project.webhook_url)
        self.assertIsNone(project.webhook_secret)

    def test_project_webhook_fields_can_be_set(self):
        """Test that webhook fields can be set"""
        project = Project.objects.create(
            name="Test Project",
            slug="test-project",
            description="Test project description",
            organization=self.org,
            webhook_url="https://example.com/webhook",
            webhook_secret="secret-key-123",
        )

        self.assertEqual(project.webhook_url, "https://example.com/webhook")
        self.assertEqual(project.webhook_secret, "secret-key-123")

    def test_project_webhook_fields_can_be_updated(self):
        """Test that webhook fields can be updated"""
        project = Project.objects.create(
            name="Test Project", slug="test-project", description="Test project description", organization=self.org
        )

        project.webhook_url = "https://example.com/new-webhook"
        project.webhook_secret = "new-secret"
        project.save()

        project.refresh_from_db()
        self.assertEqual(project.webhook_url, "https://example.com/new-webhook")
        self.assertEqual(project.webhook_secret, "new-secret")
