"""
Test suite for critical security fixes

Tests for:
1. UpdateIssue function - Fixed token authentication vulnerability
2. UpdateIssue function - Fixed IDOR vulnerability  
3. bounty_payout function - Added HMAC signature validation

Run with: python manage.py test test_security_fixes
"""

import hashlib
import hmac
import json
import time
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase

from website.models import Domain, GitHubIssue, Issue, Organization, Repo
from website.views.bounty import verify_webhook_signature


class UpdateIssueSecurityTest(TestCase):
    """Test security fixes for UpdateIssue function"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()

        # Create users
        self.user1 = User.objects.create_user(username="user1", password="testpass123")
        self.user2 = User.objects.create_user(username="user2", password="testpass123")
        self.admin = User.objects.create_superuser(username="admin", password="adminpass123")

        # Create domain
        self.domain = Domain.objects.create(name="example.com", url="https://example.com", email="admin@example.com")

        # Create issues
        self.issue1 = Issue.objects.create(
            user=self.user1, domain=self.domain, url="https://example.com/bug1", description="Test bug 1", status="open"
        )

        self.issue2 = Issue.objects.create(
            user=self.user2, domain=self.domain, url="https://example.com/bug2", description="Test bug 2", status="open"
        )

    def test_update_issue_requires_authentication(self):
        """Test that UpdateIssue requires authentication"""
        response = self.client.post("/issue/update/", {"issue_pk": self.issue1.pk, "action": "close"})

        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login", response.url)

    def test_update_issue_prevents_idor(self):
        """Test that users cannot update other users' issues (IDOR prevention)"""
        self.client.login(username="user2", password="testpass123")

        response = self.client.post(
            "/issue/update/",
            {
                "issue_pk": self.issue1.pk,  # user2 trying to update user1's issue
                "action": "close",
            },
        )

        # Should return 404 (not 403) to prevent information disclosure
        self.assertEqual(response.status_code, 404)

        # Verify issue was not modified
        self.issue1.refresh_from_db()
        self.assertEqual(self.issue1.status, "open")

    def test_update_issue_allows_owner(self):
        """Test that issue owner can update their own issue"""
        self.client.login(username="user1", password="testpass123")

        response = self.client.post("/issue/update/", {"issue_pk": self.issue1.pk, "action": "close"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Updated")

        # Verify issue was modified
        self.issue1.refresh_from_db()
        self.assertEqual(self.issue1.status, "closed")
        self.assertEqual(self.issue1.closed_by, self.user1)

    def test_update_issue_allows_superuser(self):
        """Test that superuser can update any issue"""
        self.client.login(username="admin", password="adminpass123")

        response = self.client.post("/issue/update/", {"issue_pk": self.issue2.pk, "action": "close"})

        self.assertEqual(response.status_code, 200)

        # Verify issue was modified
        self.issue2.refresh_from_db()
        self.assertEqual(self.issue2.status, "closed")

    def test_update_issue_validates_input(self):
        """Test that UpdateIssue validates input properly"""
        self.client.login(username="user1", password="testpass123")

        # Test missing issue_pk
        response = self.client.post("/issue/update/", {"action": "close"})
        self.assertEqual(response.status_code, 400)

        # Test invalid issue_pk
        response = self.client.post("/issue/update/", {"issue_pk": "invalid", "action": "close"})
        self.assertEqual(response.status_code, 400)

        # Test invalid action
        response = self.client.post(
            "/issue/update/",
            {
                "issue_pk": self.issue1.pk,
                "action": "delete",  # Invalid action
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_update_issue_no_token_authentication(self):
        """Test that old insecure token authentication is removed"""
        # Try to use token in POST data (old vulnerable method)
        response = self.client.post(
            "/issue/update/",
            {
                "issue_pk": self.issue1.pk,
                "action": "close",
                "token": "some_token",  # This should be ignored
            },
        )

        # Should require proper authentication, not accept token
        self.assertEqual(response.status_code, 302)  # Redirect to login


class BountyPayoutSecurityTest(TestCase):
    """Test security fixes for bounty_payout function"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()

        # Create organization and repo
        self.org = Organization.objects.create(name="TestOrg", url="https://github.com/testorg")

        self.repo = Repo.objects.create(
            name="test-repo", organization=self.org, repo_url="https://github.com/testorg/test-repo"
        )

        # Create GitHub issue with all required fields
        from django.utils import timezone

        now = timezone.now()

        self.github_issue = GitHubIssue.objects.create(
            issue_id=123,
            repo=self.repo,
            title="Test Issue",
            state="closed",
            url="https://github.com/testorg/test-repo/issues/123",
            created_at=now,
            updated_at=now,
        )

        self.webhook_secret = "test_webhook_secret_key"
        self.api_token = "test_api_token"

    def test_verify_webhook_signature_valid(self):
        """Test HMAC signature verification with valid signature"""
        payload = b'{"test": "data"}'
        signature = hmac.new(self.webhook_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

        signature_header = f"sha256={signature}"

        result = verify_webhook_signature(payload, signature_header, self.webhook_secret)
        self.assertTrue(result)

    def test_verify_webhook_signature_invalid(self):
        """Test HMAC signature verification with invalid signature"""
        payload = b'{"test": "data"}'
        signature_header = "sha256=invalid_signature"

        result = verify_webhook_signature(payload, signature_header, self.webhook_secret)
        self.assertFalse(result)

    def test_verify_webhook_signature_wrong_algorithm(self):
        """Test HMAC signature verification rejects wrong algorithm"""
        payload = b'{"test": "data"}'
        signature = hmac.new(self.webhook_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

        signature_header = f"sha1={signature}"  # Wrong algorithm

        result = verify_webhook_signature(payload, signature_header, self.webhook_secret)
        self.assertFalse(result)

    @patch.dict("os.environ", {"BLT_WEBHOOK_SECRET": "test_secret"})
    @patch("website.views.bounty.process_github_sponsors_payment")
    def test_bounty_payout_with_valid_signature(self, mock_payment):
        """Test bounty_payout accepts valid HMAC signature"""
        mock_payment.return_value = "tx_12345"

        payload = {
            "issue_number": 123,
            "repo": "test-repo",
            "owner": "TestOrg",
            "contributor_username": "testuser",
            "pr_number": 456,
            "bounty_amount": 5000,
            "timestamp": int(time.time()),
        }

        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = hmac.new(b"test_secret", payload_bytes, hashlib.sha256).hexdigest()

        response = self.client.post(
            "/bounty_payout/",
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_BLT_SIGNATURE=f"sha256={signature}",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")

    @patch.dict("os.environ", {"BLT_WEBHOOK_SECRET": "test_secret"})
    def test_bounty_payout_rejects_invalid_signature(self):
        """Test bounty_payout rejects invalid HMAC signature"""
        payload = {
            "issue_number": 123,
            "repo": "test-repo",
            "owner": "TestOrg",
            "contributor_username": "testuser",
            "pr_number": 456,
            "bounty_amount": 5000,
        }

        response = self.client.post(
            "/bounty_payout/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_BLT_SIGNATURE="sha256=invalid_signature",
        )

        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertEqual(data["status"], "error")

    @patch.dict("os.environ", {"BLT_API_TOKEN": "test_token"})
    @patch("website.views.bounty.process_github_sponsors_payment")
    def test_bounty_payout_fallback_to_api_token(self, mock_payment):
        """Test bounty_payout falls back to API token if no signature"""
        mock_payment.return_value = "tx_12345"

        payload = {
            "issue_number": 123,
            "repo": "test-repo",
            "owner": "TestOrg",
            "contributor_username": "testuser",
            "pr_number": 456,
            "bounty_amount": 5000,
            "timestamp": int(time.time()),
        }

        response = self.client.post(
            "/bounty_payout/",
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_BLT_API_TOKEN="test_token",
        )

        self.assertEqual(response.status_code, 200)

    @patch.dict("os.environ", {"BLT_WEBHOOK_SECRET": "test_secret"})
    def test_bounty_payout_validates_timestamp(self):
        """Test bounty_payout rejects old timestamps (replay attack prevention)"""
        old_timestamp = int(time.time()) - 400  # 6+ minutes ago

        payload = {
            "issue_number": 123,
            "repo": "test-repo",
            "owner": "TestOrg",
            "contributor_username": "testuser",
            "pr_number": 456,
            "bounty_amount": 5000,
            "timestamp": old_timestamp,
        }

        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = hmac.new(b"test_secret", payload_bytes, hashlib.sha256).hexdigest()

        response = self.client.post(
            "/bounty_payout/",
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_BLT_SIGNATURE=f"sha256={signature}",
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("timestamp", data["message"].lower())

    @patch.dict("os.environ", {"BLT_WEBHOOK_SECRET": "test_secret"})
    @patch("website.views.bounty.process_github_sponsors_payment")
    def test_bounty_payout_idempotency(self, mock_payment):
        """Test bounty_payout prevents duplicate payments"""
        # Set transaction ID to simulate already processed payment
        self.github_issue.sponsors_tx_id = "existing_tx_123"
        self.github_issue.save()

        payload = {
            "issue_number": 123,
            "repo": "test-repo",
            "owner": "TestOrg",
            "contributor_username": "testuser",
            "pr_number": 456,
            "bounty_amount": 5000,
            "timestamp": int(time.time()),
        }

        payload_bytes = json.dumps(payload).encode("utf-8")
        signature = hmac.new(b"test_secret", payload_bytes, hashlib.sha256).hexdigest()

        response = self.client.post(
            "/bounty_payout/",
            data=payload_bytes,
            content_type="application/json",
            HTTP_X_BLT_SIGNATURE=f"sha256={signature}",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "warning")
        self.assertIn("already processed", data["message"])

        # Verify payment function was not called
        mock_payment.assert_not_called()


if __name__ == "__main__":
    import django

    django.setup()
    from django.conf import settings
    from django.test.utils import get_runner

    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["test_security_fixes"])
