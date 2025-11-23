import json
from unittest.mock import patch

from allauth.socialaccount.models import SocialAccount
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from website.models import GitHubIssue, Repo, UserProfile


class BountyPayoutAPITest(TestCase):
    def setUp(self):
        # Create a test user with GitHub social account
        self.user = User.objects.create_user(username="testuser", email="test@example.com")
        # Get the auto-created UserProfile
        self.user_profile = UserProfile.objects.get(user=self.user)
        self.social_account = SocialAccount.objects.create(
            user=self.user, provider="github", uid="12345", extra_data={"login": "testuser"}
        )

        self.client = Client()
        self.api_url = reverse("process_bounty_payout")

    @patch("website.views.organization.requests.get")
    def test_bounty_payout_success(self, mock_get):
        """Test successful bounty payout processing"""
        # Mock GitHub API response
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "id": 123456,
            "title": "Test Issue",
            "state": "closed",
            "body": "Test body",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "closed_at": "2024-01-01T00:00:00Z",
            "labels": [{"name": "$5"}],
            "assignee": {"login": "testuser"},
        }

        # Make API request
        with self.settings(BLT_API_TOKEN="test-token", BLT_ALLOWED_BOUNTY_REPOS={"OWASP-BLT/BLT"}):
            response = self.client.post(
                self.api_url,
                data=json.dumps(
                    {
                        "issue_url": "https://github.com/OWASP-BLT/BLT/issues/123",
                        "pr_url": "https://github.com/OWASP-BLT/BLT/pull/456",
                    }
                ),
                content_type="application/json",
                HTTP_X_BLT_API_TOKEN="test-token",
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["amount"], 5)
        self.assertEqual(data["payment_method"], "sponsors")

        # Verify GitHubIssue was created
        issue = GitHubIssue.objects.get(issue_id=123456)
        self.assertEqual(issue.title, "Test Issue")
        self.assertEqual(issue.p2p_amount_usd, 5)
        self.assertIsNotNone(issue.sponsors_tx_id)
        self.assertIsNotNone(issue.p2p_payment_created_at)

    def test_bounty_payout_invalid_token(self):
        """Test API request with invalid token"""
        with self.settings(BLT_API_TOKEN="test-token"):
            response = self.client.post(
                self.api_url,
                data=json.dumps({"issue_url": "https://github.com/OWASP-BLT/BLT/issues/123"}),
                content_type="application/json",
                HTTP_X_BLT_API_TOKEN="wrong-token",
            )

        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data["success"])

    def test_bounty_payout_missing_issue_url(self):
        """Test API request without issue_url"""
        with self.settings(BLT_API_TOKEN="test-token"):
            response = self.client.post(
                self.api_url,
                data=json.dumps({}),
                content_type="application/json",
                HTTP_X_BLT_API_TOKEN="test-token",
            )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])

    @patch("website.views.organization.requests.get")
    def test_bounty_payout_duplicate_payment(self, mock_get):
        """Test duplicate payment prevention"""
        # Create an existing issue with payment
        repo = Repo.objects.create(
            repo_url="https://github.com/OWASP-BLT/BLT", name="BLT", slug="OWASP-BLT-BLT"
        )
        from django.utils import timezone

        GitHubIssue.objects.create(
            issue_id=123456,
            repo=repo,
            title="Test Issue",
            state="closed",
            url="https://github.com/OWASP-BLT/BLT/issues/123",
            sponsors_tx_id="existing_tx_id",
            user_profile=self.user_profile,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

        # Mock GitHub API response
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "id": 123456,
            "title": "Test Issue",
            "state": "closed",
            "labels": [{"name": "$5"}],
            "assignee": {"login": "testuser"},
        }

        with self.settings(BLT_API_TOKEN="test-token", BLT_ALLOWED_BOUNTY_REPOS={"OWASP-BLT/BLT"}):
            response = self.client.post(
                self.api_url,
                data=json.dumps({"issue_url": "https://github.com/OWASP-BLT/BLT/issues/123"}),
                content_type="application/json",
                HTTP_X_BLT_API_TOKEN="test-token",
            )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("already paid", data["error"])
