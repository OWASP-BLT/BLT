import json
import os
from unittest.mock import patch

from django.test import Client, TestCase

from website.models import GitHubIssue, Organization, Repo


class BountyPayoutTestCase(TestCase):
    """Test cases for the bounty payout functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create organization with github_org set (used for repo lookup)
        self.org = Organization.objects.create(name="TestOrg", url="https://github.com/TestOrg", github_org="TestOrg")

        # Create repository
        self.repo = Repo.objects.create(
            name="TestRepo", organization=self.org, repo_url="https://github.com/TestOrg/TestRepo"
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

    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"})
    def test_bounty_payout_success(self):
        """Test successful bounty recording."""
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
        self.assertEqual(response_data["status"], "success")
        self.assertEqual(response_data["amount"], 5000)
        self.assertEqual(response_data["recipient"], "testuser")

        # Verify database was updated
        self.issue.refresh_from_db()
        self.assertIsNotNone(self.issue.sponsors_tx_id)

    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"})
    def test_bounty_payout_duplicate(self):
        """Test that duplicate payments are rejected."""
        self.issue.sponsors_tx_id = "EXISTING_TX"
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

    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"})
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

    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"})
    def test_bounty_payout_missing_fields(self):
        """Test that missing fields are rejected."""
        payload = {"issue_number": 123, "repo": "TestRepo"}

        response = self.client.post(
            "/bounty_payout/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_BLT_API_TOKEN=self.api_token,
        )

        self.assertEqual(response.status_code, 400)

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

    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"})
    def test_bounty_payout_issue_not_found(self):
        """Test that non-existent issue is handled."""
        payload = {
            "issue_number": 999,
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

    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"})
    def test_bounty_payout_legacy_org_fallback(self):
        """Test fallback to organization matching by name when github_org is not set."""
        # Create legacy organization without github_org
        legacy_org = Organization.objects.create(name="LegacyOrg", url="https://github.com/LegacyOrg")
        legacy_repo = Repo.objects.create(
            name="LegacyRepo", organization=legacy_org, repo_url="https://github.com/LegacyOrg/LegacyRepo"
        )
        GitHubIssue.objects.create(
            issue_id=999,
            title="Legacy Issue",
            state="open",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            url="https://github.com/LegacyOrg/LegacyRepo/issues/999",
            has_dollar_tag=True,
            repo=legacy_repo,
        )

        payload = {
            "issue_number": 999,
            "repo": "LegacyRepo",
            "owner": "LegacyOrg",  # Matches name but github_org is null
            "contributor_username": "legacyuser",
            "pr_number": 789,
            "bounty_amount": 3000,
        }

        response = self.client.post(
            "/bounty_payout/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_BLT_API_TOKEN=self.api_token,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"})
    def test_bounty_payout_negative_amount(self):
        """Test that negative bounty amounts are rejected."""
        payload = {
            "issue_number": 123,
            "repo": "TestRepo",
            "owner": "TestOrg",
            "contributor_username": "testuser",
            "pr_number": 456,
            "bounty_amount": -5000,
        }

        response = self.client.post(
            "/bounty_payout/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_BLT_API_TOKEN=self.api_token,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("positive", response.json()["message"])

    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"})
    def test_bounty_payout_zero_amount(self):
        """Test that zero bounty amounts are rejected."""
        payload = {
            "issue_number": 123,
            "repo": "TestRepo",
            "owner": "TestOrg",
            "contributor_username": "testuser",
            "pr_number": 456,
            "bounty_amount": 0,
        }

        response = self.client.post(
            "/bounty_payout/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_BLT_API_TOKEN=self.api_token,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("positive", response.json()["message"])

    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"})
    def test_bounty_payout_excessive_amount(self):
        """Test that bounty amounts exceeding $1M are rejected."""
        payload = {
            "issue_number": 123,
            "repo": "TestRepo",
            "owner": "TestOrg",
            "contributor_username": "testuser",
            "pr_number": 456,
            "bounty_amount": 100000001,  # Over $1M
        }

        response = self.client.post(
            "/bounty_payout/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_BLT_API_TOKEN=self.api_token,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("exceeds maximum", response.json()["message"])

    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"})
    def test_bounty_payout_invalid_owner(self):
        """Test that invalid owner names are rejected."""
        payload = {
            "issue_number": 123,
            "repo": "TestRepo",
            "owner": "Invalid Owner!@#",  # Invalid characters
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

        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid owner", response.json()["message"])

    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"})
    def test_bounty_payout_invalid_username(self):
        """Test that invalid usernames are rejected."""
        payload = {
            "issue_number": 123,
            "repo": "TestRepo",
            "owner": "TestOrg",
            "contributor_username": "user.name.with.dots",  # Dots not allowed in usernames
            "pr_number": 456,
            "bounty_amount": 5000,
        }

        response = self.client.post(
            "/bounty_payout/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_BLT_API_TOKEN=self.api_token,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid username", response.json()["message"])

