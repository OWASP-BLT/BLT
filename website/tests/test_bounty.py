import json
import os
from unittest.mock import patch

from django.test import Client, TestCase
from django.test.utils import override_settings

from website.models import GitHubIssue, Organization, Repo


class BountyPayoutTestCase(TestCase):
    """Test cases for the minimal bounty payout functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create organization
        self.org = Organization.objects.create(name="TestOrg", url="https://github.com/TestOrg")

        # Create repository
        self.repo = Repo.objects.create(
            name="TestRepo", organization=self.org, url="https://github.com/TestOrg/TestRepo"
        )

        # Create GitHub issue with bounty
        self.issue = GitHubIssue.objects.create(
            issue_id=123,
            title="Test Issue with Bounty",
            body="This is a test issue",
            state="open",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            url="https://github.com/TestOrg/TestRepo/issues/123",
            has_dollar_tag=True,
            repo=self.repo,
        )

        # Set up API token for tests
        self.api_token = "test_token_12345"

    @override_settings(BLT_API_TOKEN="test_token_12345")
    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"})
    def test_bounty_payout_success(self):
        """Test successful bounty payout."""
        payload = {
            "issue_number": 123,
            "repo": "TestRepo",
            "owner": "TestOrg",
            "contributor_username": "testuser",
            "pr_number": 456,
            "bounty_amount": 5000,  # $50.00
        }

        response = self.client.post(
            "/bounty_payout/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_BLT_API_TOKEN=self.api_token,
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["status"], "success")
        self.assertEqual(response_data["amount"], 5000)
        self.assertEqual(response_data["recipient"], "testuser")
        self.assertIn("transaction_id", response_data)

        # Verify database was updated
        self.issue.refresh_from_db()
        self.assertIsNotNone(self.issue.sponsors_tx_id)

    @override_settings(BLT_API_TOKEN="test_token_12345")
    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"})
    def test_bounty_payout_duplicate_payment(self):
        """Test that duplicate payments are rejected."""
        # Set transaction ID to simulate previous payment
        self.issue.sponsors_tx_id = "TXN-123-456"
        self.issue.save()

        payload = {
            "issue_number": 123,
            "repo": "TestRepo",
            "owner": "TestOrg",
            "contributor_username": "testuser",
            "pr_number": 456,
            "bounty_amount": 5000,
        }

        response = self.client.post(
            "/bounty_payout/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_BLT_API_TOKEN=self.api_token,
        )

        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data["status"], "warning")
        self.assertIn("already processed", response_data["message"])

    def test_bounty_payout_unauthorized(self):
        """Test that invalid API token is rejected."""
        payload = {
            "issue_number": 123,
            "repo": "TestRepo",
            "owner": "TestOrg",
            "contributor_username": "testuser",
            "pr_number": 456,
            "bounty_amount": 5000,
        }

        response = self.client.post(
            "/bounty_payout/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_BLT_API_TOKEN="wrong_token",
        )

        self.assertEqual(response.status_code, 403)
        response_data = response.json()
        self.assertEqual(response_data["status"], "error")
        self.assertEqual(response_data["message"], "Unauthorized")

    @override_settings(BLT_API_TOKEN="test_token_12345")
    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"})
    def test_bounty_payout_missing_fields(self):
        """Test that missing fields are rejected."""
        payload = {
            "issue_number": 123,
            "repo": "TestRepo",
            # Missing owner, contributor_username, pr_number, bounty_amount
        }

        response = self.client.post(
            "/bounty_payout/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_BLT_API_TOKEN=self.api_token,
        )

        self.assertEqual(response.status_code, 400)
        response_data = response.json()
        self.assertEqual(response_data["status"], "error")
        self.assertIn("Missing required fields", response_data["message"])

    @override_settings(BLT_API_TOKEN="test_token_12345")
    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"})
    def test_bounty_payout_repo_not_found(self):
        """Test that non-existent repository is handled."""
        payload = {
            "issue_number": 123,
            "repo": "NonExistentRepo",
            "owner": "TestOrg",
            "contributor_username": "testuser",
            "pr_number": 456,
            "bounty_amount": 5000,
        }

        response = self.client.post(
            "/bounty_payout/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_BLT_API_TOKEN=self.api_token,
        )

        self.assertEqual(response.status_code, 404)
        response_data = response.json()
        self.assertEqual(response_data["status"], "error")
        self.assertIn("Repository not found", response_data["message"])

    @override_settings(BLT_API_TOKEN="test_token_12345")
    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"})
    def test_bounty_payout_issue_not_found(self):
        """Test that non-existent issue is handled."""
        payload = {
            "issue_number": 999,  # Non-existent issue
            "repo": "TestRepo",
            "owner": "TestOrg",
            "contributor_username": "testuser",
            "pr_number": 456,
            "bounty_amount": 5000,
        }

        response = self.client.post(
            "/bounty_payout/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_BLT_API_TOKEN=self.api_token,
        )

        self.assertEqual(response.status_code, 404)
        response_data = response.json()
        self.assertEqual(response_data["status"], "error")
        self.assertIn("Issue not found", response_data["message"])
