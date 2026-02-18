import json
import os
from datetime import timedelta
from unittest.mock import patch

from django.test import Client, TestCase
from django.utils import timezone

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

    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345", "GITHUB_TOKEN": "test_github_token"})
    @patch("website.views.bounty.process_github_sponsors_payment")
    def test_bounty_payout_success(self, mock_payment):
        """Test successful bounty payout with mocked GitHub Sponsors API."""
        # Mock successful payment
        mock_payment.return_value = "SPONSORSHIP_ID_12345"

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
        self.assertEqual(response_data["transaction_id"], "SPONSORSHIP_ID_12345")

        # Verify database was updated
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.sponsors_tx_id, "SPONSORSHIP_ID_12345")

        # Verify payment function was called with correct parameters
        mock_payment.assert_called_once()
        call_args = mock_payment.call_args
        self.assertEqual(call_args[1]["username"], "testuser")
        self.assertEqual(call_args[1]["amount"], 5000)

    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"})
    def test_timed_bounty_endpoint_records_expiry(self):
        expiry = (timezone.now() + timedelta(hours=5)).isoformat()
        payload = {
            "issue_number": 123,
            "repo": "TestRepo",
            "owner": "TestOrg",
            "bounty_expiry_date": expiry,
        }

        response = self.client.post(
            "/timed_bounty/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_BLT_API_TOKEN=self.api_token,
        )

        self.assertEqual(response.status_code, 200)
        self.issue.refresh_from_db()
        self.assertIsNotNone(self.issue.bounty_expiry_date)

    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"})
    def test_timed_bounty_endpoint_invalid_datetime(self):
        payload = {
            "issue_number": 123,
            "repo": "TestRepo",
            "owner": "TestOrg",
            "bounty_expiry_date": "not-a-date",
        }

        response = self.client.post(
            "/timed_bounty/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_BLT_API_TOKEN=self.api_token,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid bounty_expiry_date", response.json()["message"])

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
        response_data = response.json()
        self.assertEqual(response_data["status"], "error")
        self.assertEqual(response_data["message"], "Unauthorized")

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

    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345", "GITHUB_TOKEN": "test_github_token"})
    @patch("website.views.bounty.process_github_sponsors_payment")
    def test_bounty_payout_payment_failure(self, mock_payment):
        """Test that payment processing failure is handled correctly."""
        # Mock failed payment (returns None)
        mock_payment.return_value = None

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

        self.assertEqual(response.status_code, 500)
        response_data = response.json()
        self.assertEqual(response_data["status"], "error")
        self.assertIn("Payment processing failed", response_data["message"])

        # Verify database was NOT updated
        self.issue.refresh_from_db()
        self.assertIsNone(self.issue.sponsors_tx_id)

    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345", "GITHUB_TOKEN": "test_github_token"})
    @patch("website.views.bounty.process_github_sponsors_payment")
    def test_bounty_payout_timed_not_expired(self, mock_payment):
        mock_payment.return_value = "SPONSORSHIP_ID_67890"
        self.issue.bounty_expiry_date = timezone.now() + timedelta(hours=2)
        self.issue.save()

        payload = {
            "issue_number": 123,
            "repo": "TestRepo",
            "owner": "TestOrg",
            "contributor_username": "testuser",
            "pr_number": 456,
            "bounty_amount": 5000,
            "is_timed_bounty": True,
        }

        response = self.client.post(
            "/bounty_payout/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_BLT_API_TOKEN=self.api_token,
        )

        self.assertEqual(response.status_code, 200)
        mock_payment.assert_called_once()

    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345", "GITHUB_TOKEN": "test_github_token"})
    @patch("website.views.bounty.process_github_sponsors_payment")
    def test_bounty_payout_timed_expired(self, mock_payment):
        self.issue.bounty_expiry_date = timezone.now() - timedelta(hours=1)
        self.issue.save()

        payload = {
            "issue_number": 123,
            "repo": "TestRepo",
            "owner": "TestOrg",
            "contributor_username": "testuser",
            "pr_number": 456,
            "bounty_amount": 5000,
            "is_timed_bounty": True,
        }

        response = self.client.post(
            "/bounty_payout/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_BLT_API_TOKEN=self.api_token,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Bounty expired", response.json()["message"])
        mock_payment.assert_not_called()

    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"})
    def test_bounty_payout_blocked_when_payment_pending(self):
        """Test that a second payout attempt is blocked while payment_pending is True."""
        self.issue.payment_pending = True
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

        self.assertEqual(response.status_code, 202)
        response_data = response.json()
        self.assertEqual(response_data["status"], "warning")
        self.assertIn("already in progress", response_data["message"])

    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345", "GITHUB_TOKEN": "test_github_token"})
    @patch("website.views.bounty.process_github_sponsors_payment")
    def test_payment_pending_cleared_after_success(self, mock_payment):
        """Test that payment_pending is False after a successful payment."""
        mock_payment.return_value = "SPONSORSHIP_OK"

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
        self.issue.refresh_from_db()
        self.assertFalse(self.issue.payment_pending)

    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345", "GITHUB_TOKEN": "test_github_token"})
    @patch("website.views.bounty.process_github_sponsors_payment")
    def test_payment_pending_cleared_after_failure(self, mock_payment):
        """Test that payment_pending is reset to False when payment processing fails."""
        mock_payment.return_value = None

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

        self.assertEqual(response.status_code, 500)
        self.issue.refresh_from_db()
        self.assertFalse(self.issue.payment_pending)

    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"})
    @patch("website.views.bounty.process_github_sponsors_payment")
    def test_bounty_payout_timed_missing_expiry(self, mock_payment):
        payload = {
            "issue_number": 123,
            "repo": "TestRepo",
            "owner": "TestOrg",
            "contributor_username": "testuser",
            "pr_number": 456,
            "bounty_amount": 5000,
            "is_timed_bounty": True,
        }

        response = self.client.post(
            "/bounty_payout/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_BLT_API_TOKEN=self.api_token,
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("Timed bounty expiry date not set", response.json()["message"])
        mock_payment.assert_not_called()
