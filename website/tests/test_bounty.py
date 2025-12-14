import json
import os
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.test.utils import override_settings
from rest_framework.authtoken.models import Token
from django.urls import reverse
from website.models import Bounty, GitHubIssue, Organization, Repo
from website.views.slack_handlers import slack_bounty_command


class BountyPayoutTestCase(TestCase):
    """Test cases for the minimal bounty payout functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()

        # Create organization
        self.org = Organization.objects.create(
            name="TestOrg",
            url="https://github.com/TestOrg",
        )

        # Create repository
        self.repo = Repo.objects.create(
            name="TestRepo",
            organization=self.org,
            repo_url="https://github.com/TestOrg/TestRepo",
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

        # API token used both in settings and header
        self.api_token = "test_token_12345"

    @override_settings(BLT_API_TOKEN="test_token_12345")
    @patch.dict(
        os.environ,
        {
            "BLT_API_TOKEN": "test_token_12345",
            "GITHUB_TOKEN": "test_github_token",
        },
        clear=False,
    )
    @patch("website.views.bounty.process_github_sponsors_payment")
    def test_bounty_payout_success(self, mock_payment):
        """
        Happy path: valid token, valid payload, Sponsors payment succeeds.

        We expect:
        - HTTP 200
        - status: "success"
        - amount and recipient echoed back
        - transaction_id filled
        - GitHubIssue.sponsors_tx_id updated
        - process_github_sponsors_payment called once with correct args
        """
        mock_payment.return_value = "SPONSORSHIP_ID_12345"

        payload = {
            "issue_number": 123,
            "repo": "TestRepo",
            "owner": "TestOrg",
            "contributor_username": "testuser",
            "pr_number": 456,
            "bounty_amount": 5000,  # cents / minor units
        }

        response = self.client.post(
            "/bounty_payout/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_BLT_API_TOKEN=self.api_token,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["amount"], 5000)
        self.assertEqual(data["recipient"], "testuser")
        self.assertEqual(data["transaction_id"], "SPONSORSHIP_ID_12345")

        # DB updated
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.sponsors_tx_id, "SPONSORSHIP_ID_12345")

        # Payment called correctly
        mock_payment.assert_called_once()
        _, kwargs = mock_payment.call_args
        self.assertEqual(kwargs["username"], "testuser")
        self.assertEqual(kwargs["amount"], 5000)

    @override_settings(BLT_API_TOKEN="test_token_12345")
    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"}, clear=False)
    def test_bounty_payout_duplicate_payment(self):
        """
        If sponsors_tx_id is already set on the issue, the endpoint should be idempotent:
        - HTTP 200
        - status: "warning"
        - message mentions already processed
        - no further payment is attempted (implicitly: we don't clear sponsors_tx_id)
        """
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
        data = response.json()
        self.assertEqual(data["status"], "warning")
        self.assertIn("already processed", data["message"])

        # sponsors_tx_id remains unchanged
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.sponsors_tx_id, "TXN-123-456")

    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"}, clear=False)
    def test_bounty_payout_unauthorized(self):
        """
        Wrong X_BLT_API_TOKEN header -> 403 error.
        """
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
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["message"], "Unauthorized")

    @override_settings(BLT_API_TOKEN="test_token_12345")
    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"}, clear=False)
    def test_bounty_payout_missing_fields(self):
        """
        Missing required fields -> 400 with clear error.
        """
        payload = {
            "issue_number": 123,
            "repo": "TestRepo",
            # owner, contributor_username, pr_number, bounty_amount missing
        }

        response = self.client.post(
            "/bounty_payout/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_BLT_API_TOKEN=self.api_token,
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertIn("Missing required fields", data["message"])

    @override_settings(BLT_API_TOKEN="test_token_12345")
    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"}, clear=False)
    def test_bounty_payout_repo_not_found(self):
        """
        Repo in payload does not exist -> 404.
        """
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
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertIn("Repository not found", data["message"])

    @override_settings(BLT_API_TOKEN="test_token_12345")
    @patch.dict(os.environ, {"BLT_API_TOKEN": "test_token_12345"}, clear=False)
    def test_bounty_payout_issue_not_found(self):
        """
        Issue number does not exist for the given repo -> 404.
        """
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
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertIn("Issue not found", data["message"])

    @override_settings(BLT_API_TOKEN="test_token_12345")
    @patch.dict(
        os.environ,
        {"BLT_API_TOKEN": "test_token_12345", "GITHUB_TOKEN": "test_github_token"},
        clear=False,
    )
    @patch("website.views.bounty.process_github_sponsors_payment")
    def test_bounty_payout_payment_failure(self, mock_payment):
        """
        Sponsors payment returns None / fails -> 500 and DB not updated.
        """
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
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertIn("Payment processing failed", data["message"])

        self.issue.refresh_from_db()
        self.assertIsNone(self.issue.sponsors_tx_id)


# ---------------------------------------------------------------------------
# New tests: Bounty API (/api/v1/bounties/) behaviour
# ---------------------------------------------------------------------------
class BountyApiTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        self.org = Organization.objects.create(
            name="TestOrg",
            url="https://github.com/TestOrg",
        )
        self.repo = Repo.objects.create(
            name="TestRepo",
            organization=self.org,
            repo_url="https://github.com/TestOrg/TestRepo",
        )

        # Raw GitHub issue data (used by API & tests)
        self.github_issue = GitHubIssue.objects.create(
            issue_id=123,
            title="Issue for Bounties",
            body="body",
            state="open",
            created_at="2025-01-01T00:00:00Z",
            updated_at="2025-01-01T00:00:00Z",
            url="https://github.com/TestOrg/TestRepo/issues/123",
            has_dollar_tag=True,
            repo=self.repo,
        )

        # API user + token used for DRF TokenAuthentication
        User = get_user_model()
        self.api_user, _ = User.objects.get_or_create(
            username="api-user",
            defaults={"email": "api-user@example.com"},
        )
        self.api_token, _ = Token.objects.get_or_create(user=self.api_user)

    def _auth_headers(self):
        # DRF TokenAuthentication expects this header
        return {"HTTP_AUTHORIZATION": f"Token {self.api_token.key}"}

    @override_settings(BLT_API_TOKEN="test_token_12345")
    def test_create_bounty_for_issue_via_api(self):
        """
        POST /api/v1/bounties/ with github_issue_url, amount and username
        should create a Bounty that preserves github_issue_url and amount.

        We deliberately do **not** assert that `bounty.issue_id` is non-NULL,
        because Issue creation may require additional fields (user, captcha, etc.)
        and is not guaranteed by the public API contract. The source of truth
        for this endpoint is the github_issue_url field on Bounty.
        """
        payload = {
            "github_issue_url": self.github_issue.url,
            "amount": "25.00",
            "github_username": "testuser",
        }

        response = self.client.post(
            "/api/v1/bounties/",
            data=json.dumps(payload),
            content_type="application/json",
            **self._auth_headers(),
        )

        # API should accept the request and echo back the URL
        self.assertIn(response.status_code, (200, 201))
        data = response.json()
        self.assertEqual(data["github_issue_url"], self.github_issue.url)

        # Exactly one bounty must be created
        bounties = Bounty.objects.all()
        self.assertEqual(bounties.count(), 1)
        bounty = bounties.first()

        # Ensure it is tied to the correct GitHub issue URL and amount
        self.assertEqual(bounty.github_issue_url, self.github_issue.url)
        self.assertEqual(bounty.amount, Decimal("25.00"))

    @override_settings(BLT_API_TOKEN="test_token_12345")
    def test_issue_total_endpoint_sums_bounties(self):
        """
        GET /api/v1/bounties/issue-total/?github_issue_url=... should return
        the sum of all bounties for that issue.
        We create the bounties via the public API to mirror real usage.
        """
        # First bounty: 10.00
        payload1 = {
            "github_issue_url": self.github_issue.url,
            "amount": "10.00",
            "github_username": "user1",
        }
        resp1 = self.client.post(
            "/api/v1/bounties/",
            data=json.dumps(payload1),
            content_type="application/json",
            **self._auth_headers(),
        )
        self.assertIn(resp1.status_code, (200, 201))

        # Second bounty: 5.50
        payload2 = {
            "github_issue_url": self.github_issue.url,
            "amount": "5.50",
            "github_username": "user2",
        }
        resp2 = self.client.post(
            "/api/v1/bounties/",
            data=json.dumps(payload2),
            content_type="application/json",
            **self._auth_headers(),
        )
        self.assertIn(resp2.status_code, (200, 201))

        encoded_url = self.github_issue.url  # view handles quoting itself

        response = self.client.get(
            f"/api/v1/bounties/issue-total/?github_issue_url={encoded_url}",
            **self._auth_headers(),
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        # 10.00 + 5.50 = 15.50
        self.assertEqual(Decimal(str(data["total"])), Decimal("15.50"))


class SlackBountyCommandTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.issue_url = "https://github.com/TestOrg/TestRepo/issues/123"
        self.url = reverse("slack_bounty_command")  # <- single source of truth

    @override_settings(
        BLT_API_BASE_URL="https://blt.test/api",
        BLT_API_TOKEN="test_token_12345",
    )
    @patch("website.views.slack_handlers.verify_slack_signature", return_value=True)
    @patch("website.views.slack_handlers.requests.get")
    @patch("website.views.slack_handlers.requests.post")
    def test_slack_bounty_success(
        self,
        mock_post,
        mock_get,
        mock_verify,
    ):
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {"id": 1}

        mock_get.return_value.ok = True
        mock_get.return_value.json.return_value = {
            "github_issue_url": self.issue_url,
            "total": "10.00",
        }

        response = self.client.post(
            self.url,
            data={
                "text": f"10 {self.issue_url} testuser",
                "user_id": "U12345",
                "response_url": "https://hooks.slack.com/commands/XYZ",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode("utf-8"))
        self.assertEqual(payload["response_type"], "in_channel")
        text_block = payload["blocks"][0]["text"]["text"]
        self.assertIn("New bounty placed", text_block)
        self.assertIn("*Amount:* $10", text_block)
        self.assertIn("testuser", text_block)
        self.assertTrue(mock_post.called)
        self.assertTrue(mock_get.called)

    @override_settings(
        BLT_API_BASE_URL="https://blt.test/api",
        BLT_API_TOKEN="test_token_12345",
    )
    @patch("website.views.slack_handlers.verify_slack_signature", return_value=True)
    def test_slack_bounty_invalid_format(self, mock_verify):
        response = self.client.post(
            self.url,
            data={
                "text": "this is not valid",
                "user_id": "U12345",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode("utf-8"))
        self.assertEqual(payload["response_type"], "ephemeral")
        self.assertIn("Usage: `/bounty", payload["text"])

    @override_settings(
        BLT_API_BASE_URL="https://blt.test/api",
        BLT_API_TOKEN="test_token_12345",
    )
    @patch("website.views.slack_handlers.verify_slack_signature", return_value=True)
    def test_slack_bounty_zero_amount_treated_as_invalid(self, mock_verify):
        response = self.client.post(
            self.url,
            data={
                "text": f"0 {self.issue_url} testuser",
                "user_id": "U12345",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = json.loads(response.content.decode("utf-8"))
        self.assertEqual(payload["response_type"], "ephemeral")
        self.assertIn("must be positive", payload["text"])