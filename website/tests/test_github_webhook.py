import json
from datetime import datetime
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from website.models import GitHubIssue, Repo, UserProfile


class GitHubWebhookTestCase(TestCase):
    """Test GitHub webhook handling for issue events"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.webhook_url = reverse("github-webhook")

        # Create test user with GitHub profile
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.user_profile = UserProfile.objects.get(user=self.user)
        self.user_profile.github_url = "https://github.com/testuser"
        self.user_profile.save()

        # Create test repository
        self.repo = Repo.objects.create(
            name="test-repo",
            repo_url="https://github.com/testorg/test-repo",
            slug="testorg-test-repo",
        )

        # Create test GitHub issue
        self.github_issue = GitHubIssue.objects.create(
            issue_id=123,
            title="Test Issue",
            body="Test issue description",
            state="open",
            type="issue",
            created_at=datetime(2024, 1, 1, 12, 0, 0),
            updated_at=datetime(2024, 1, 1, 12, 0, 0),
            url="https://github.com/testorg/test-repo/issues/123",
            repo=self.repo,
        )

    def test_webhook_closes_issue_on_github_close(self):
        """Test that webhook closes GitHubIssue when GitHub issue is closed"""
        # Create webhook payload for issue closed event
        payload = {
            "action": "closed",
            "issue": {
                "number": 123,
                "state": "closed",
                "html_url": "https://github.com/testorg/test-repo/issues/123",
                "closed_at": "2024-01-02T12:00:00Z",
                "updated_at": "2024-01-02T12:00:00Z",
            },
            "repository": {
                "full_name": "testorg/test-repo",
                "html_url": "https://github.com/testorg/test-repo",
            },
            "sender": {
                "html_url": "https://github.com/testuser",
            },
        }

        # Send webhook request
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="issues",
        )

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

        # Verify GitHubIssue was updated
        self.github_issue.refresh_from_db()
        self.assertEqual(self.github_issue.state, "closed")
        self.assertIsNotNone(self.github_issue.closed_at)

    def test_webhook_opens_issue_on_github_open(self):
        """Test that webhook updates GitHubIssue when GitHub issue is opened/reopened"""
        # First close the issue
        self.github_issue.state = "closed"
        self.github_issue.save()

        # Create webhook payload for issue opened/reopened event
        payload = {
            "action": "reopened",
            "issue": {
                "number": 123,
                "state": "open",
                "html_url": "https://github.com/testorg/test-repo/issues/123",
                "updated_at": "2024-01-03T12:00:00Z",
            },
            "repository": {
                "full_name": "testorg/test-repo",
                "html_url": "https://github.com/testorg/test-repo",
            },
            "sender": {
                "html_url": "https://github.com/testuser",
            },
        }

        # Send webhook request
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="issues",
        )

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

        # Verify GitHubIssue was updated
        self.github_issue.refresh_from_db()
        self.assertEqual(self.github_issue.state, "open")

    def test_webhook_handles_missing_issue_gracefully(self):
        """Test that webhook handles missing issues gracefully"""
        payload = {
            "action": "closed",
            "issue": {
                "number": 999,  # Non-existent issue
                "state": "closed",
                "html_url": "https://github.com/testorg/test-repo/issues/999",
                "closed_at": "2024-01-02T12:00:00Z",
                "updated_at": "2024-01-02T12:00:00Z",
            },
            "repository": {
                "full_name": "testorg/test-repo",
                "html_url": "https://github.com/testorg/test-repo",
            },
            "sender": {
                "html_url": "https://github.com/testuser",
            },
        }

        # Send webhook request
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="issues",
        )

        # Should still return success even if issue not found
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

    def test_webhook_handles_missing_repo_gracefully(self):
        """Test that webhook handles missing repos gracefully"""
        payload = {
            "action": "closed",
            "issue": {
                "number": 123,
                "state": "closed",
                "html_url": "https://github.com/unknown/unknown-repo/issues/123",
                "closed_at": "2024-01-02T12:00:00Z",
                "updated_at": "2024-01-02T12:00:00Z",
            },
            "repository": {
                "full_name": "unknown/unknown-repo",
                "html_url": "https://github.com/unknown/unknown-repo",
            },
            "sender": {
                "html_url": "https://github.com/testuser",
            },
        }

        # Send webhook request
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="issues",
        )

        # Should still return success even if repo not found
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

    def test_webhook_requires_post_method(self):
        """Test that webhook only accepts POST requests"""
        response = self.client.get(self.webhook_url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "Invalid method")

    def test_webhook_handles_malformed_payload(self):
        """Test that webhook handles malformed payloads gracefully"""
        # Missing required fields
        payload = {
            "action": "closed",
            "issue": {
                # Missing number
                "state": "closed",
            },
            "repository": {
                # Missing html_url
            },
        }

        # Send webhook request
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="issues",
        )

        # Should handle gracefully
        self.assertEqual(response.status_code, 400)

    @patch("website.views.user.assign_github_badge")
    def test_webhook_assigns_badge_on_first_issue_close(self, mock_assign_badge):
        """Test that webhook still assigns badge for first issue closed"""
        payload = {
            "action": "closed",
            "issue": {
                "number": 123,
                "state": "closed",
                "html_url": "https://github.com/testorg/test-repo/issues/123",
                "closed_at": "2024-01-02T12:00:00Z",
                "updated_at": "2024-01-02T12:00:00Z",
            },
            "repository": {
                "full_name": "testorg/test-repo",
                "html_url": "https://github.com/testorg/test-repo",
            },
            "sender": {
                "html_url": "https://github.com/testuser",
            },
        }

        # Send webhook request
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="issues",
        )

        # Check response
        self.assertEqual(response.status_code, 200)

        # Verify badge assignment was called
        mock_assign_badge.assert_called_once_with(self.user, "First Issue Closed")

    def test_webhook_updates_timestamps_correctly(self):
        """Test that webhook updates timestamps correctly"""
        payload = {
            "action": "closed",
            "issue": {
                "number": 123,
                "state": "closed",
                "html_url": "https://github.com/testorg/test-repo/issues/123",
                "closed_at": "2024-01-02T14:30:45Z",
                "updated_at": "2024-01-02T14:30:45Z",
            },
            "repository": {
                "full_name": "testorg/test-repo",
                "html_url": "https://github.com/testorg/test-repo",
            },
            "sender": {
                "html_url": "https://github.com/testuser",
            },
        }

        # Send webhook request
        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="issues",
        )

        # Check response
        self.assertEqual(response.status_code, 200)

        # Verify timestamps were updated
        self.github_issue.refresh_from_db()
        self.assertIsNotNone(self.github_issue.closed_at)
        self.assertIsNotNone(self.github_issue.updated_at)
        # Verify the time is approximately correct (within a few seconds due to parsing)
        self.assertEqual(self.github_issue.closed_at.day, 2)
        self.assertEqual(self.github_issue.closed_at.hour, 14)
