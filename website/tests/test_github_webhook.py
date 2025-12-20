import hashlib
import hmac
import json
from datetime import datetime
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from website.models import GitHubIssue, Repo, UserProfile


def compute_github_signature(secret: str, body: bytes) -> str:
    """Generate X-Hub-Signature-256 header for a given body."""
    return "sha256=" + hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()


@override_settings(GITHUB_WEBHOOK_SECRET="testsecret")
class GitHubWebhookIssuesTestCase(TestCase):
    """Test GitHub webhook handling for ISSUE events"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.webhook_url = reverse("github-webhook")
        self.secret = "testsecret"

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
            created_at=timezone.make_aware(datetime(2024, 1, 1, 12, 0, 0)),
            updated_at=timezone.make_aware(datetime(2024, 1, 1, 12, 0, 0)),
            url="https://github.com/testorg/test-repo/issues/123",
            repo=self.repo,
        )

    def _sign(self, body: bytes) -> str:
        return compute_github_signature(self.secret, body)

    def _post(self, payload: dict, event: str = "issues", *, signature=None):
        """Helper to POST to /github-webhook/ with correct headers."""
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "HTTP_X_GITHUB_EVENT": event,
        }
        if signature is None:
            signature = self._sign(body)
        headers["HTTP_X_HUB_SIGNATURE_256"] = signature

        return self.client.post(
            self.webhook_url,
            data=body,
            content_type="application/json",
            **headers,
        )

    def test_webhook_closes_issue_on_github_close(self):
        """Test that webhook closes GitHubIssue when GitHub issue is closed"""
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

        response = self._post(payload, event="issues")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

        self.github_issue.refresh_from_db()
        self.assertEqual(self.github_issue.state, "closed")
        self.assertIsNotNone(self.github_issue.closed_at)

    def test_webhook_opens_issue_on_github_open(self):
        """Test that webhook updates GitHubIssue when GitHub issue is opened/reopened"""
        # First close the issue
        self.github_issue.state = "closed"
        self.github_issue.save()

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

        response = self._post(payload, event="issues")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

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

        response = self._post(payload, event="issues")

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

        response = self._post(payload, event="issues")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")

    def test_webhook_requires_post_method(self):
        """Test that webhook only accepts POST requests"""
        response = self.client.get(self.webhook_url)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "Invalid method")

    def test_webhook_handles_malformed_payload(self):
        """Test that webhook handles malformed payloads gracefully"""
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

        # malformed payload still needs *a* signature header
        body = json.dumps(payload).encode("utf-8")
        sig = self._sign(body)

        response = self.client.post(
            self.webhook_url,
            data=body,
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="issues",
            HTTP_X_HUB_SIGNATURE_256=sig,
        )

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

        response = self._post(payload, event="issues")

        self.assertEqual(response.status_code, 200)
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

        response = self._post(payload, event="issues")

        self.assertEqual(response.status_code, 200)

        self.github_issue.refresh_from_db()
        self.assertIsNotNone(self.github_issue.closed_at)
        self.assertIsNotNone(self.github_issue.updated_at)
        self.assertEqual(self.github_issue.closed_at.day, 2)
        self.assertEqual(self.github_issue.closed_at.hour, 14)


@override_settings(GITHUB_WEBHOOK_SECRET="testsecret")
class GitHubWebhookPullRequestTestCase(TestCase):
    """Test GitHub webhook handling for PULL REQUEST events + security."""

    def setUp(self):
        """Set up a test client, webhook URL, secret, and a test Repo instance."""
        self.client = Client()
        self.webhook_url = reverse("github-webhook")
        self.secret = "testsecret"

        # Repo must exist to be linked by webhook
        self.repo_url = "https://github.com/OWASP-BLT/demo-repo"
        self.repo = Repo.objects.create(
            name="demo-repo",
            repo_url=self.repo_url,
            slug="owasp-blt-demo-repo",
        )

        self.pr_global_id = 987654321  # pull_request["id"]
        self.pr_number = 42  # pull_request["number"]

    def _sign(self, body: bytes) -> str:
        return compute_github_signature(self.secret, body)

    def _post(self, payload: dict, *, signature=None):
        """Helper to POST a signed pull_request webhook payload to /github-webhook/."""
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "HTTP_X_GITHUB_EVENT": "pull_request",
        }
        if signature is None:
            signature = self._sign(body)
        headers["HTTP_X_HUB_SIGNATURE_256"] = signature

        return self.client.post(
            self.webhook_url,
            data=body,
            content_type="application/json",
            **headers,
        )

    def test_pr_opened_creates_github_issue(self):
        """PR opened event should create a GitHubIssue of type pull_request."""
        created_at = timezone.now()
        updated_at = timezone.now()

        payload = {
            "action": "opened",
            "pull_request": {
                "id": self.pr_global_id,
                "number": self.pr_number,
                "state": "open",
                "title": "Add hackathon feature",
                "body": "This PR is for the hackathon.",
                "html_url": f"{self.repo_url}/pull/{self.pr_number}",
                "merged": False,
                "created_at": created_at.isoformat().replace("+00:00", "Z"),
                "updated_at": updated_at.isoformat().replace("+00:00", "Z"),
                "user": {
                    "login": "octocat",
                    "html_url": "https://github.com/octocat",
                    "avatar_url": "https://avatars.githubusercontent.com/u/1?v=4",
                },
            },
            "repository": {
                "full_name": "OWASP-BLT/demo-repo",
                "html_url": self.repo_url,
            },
        }

        response = self._post(payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(GitHubIssue.objects.count(), 1)

        issue = GitHubIssue.objects.first()
        self.assertEqual(issue.issue_id, self.pr_global_id)
        self.assertEqual(issue.type, "pull_request")
        self.assertEqual(issue.state, "open")
        self.assertFalse(issue.is_merged)
        self.assertEqual(issue.repo, self.repo)

    def test_pr_merged_updates_issue_and_sets_merged_at(self):
        """PR closed with merged=true should update GitHubIssue and set merged_at/closed_at."""
        # Seed with opened PR via webhook
        opened_payload = {
            "action": "opened",
            "pull_request": {
                "id": self.pr_global_id,
                "number": self.pr_number,
                "state": "open",
                "title": "Add hackathon feature",
                "body": "This PR is for the hackathon.",
                "html_url": f"{self.repo_url}/pull/{self.pr_number}",
                "merged": False,
                "created_at": timezone.now().isoformat(),
                "updated_at": timezone.now().isoformat(),
                "user": {
                    "login": "octocat",
                    "html_url": "https://github.com/octocat",
                    "avatar_url": "https://avatars.githubusercontent.com/u/1?v=4",
                },
            },
            "repository": {
                "full_name": "OWASP-BLT/demo-repo",
                "html_url": self.repo_url,
            },
        }
        self._post(opened_payload)
        self.assertEqual(GitHubIssue.objects.count(), 1)

        merged_at = timezone.now()
        closed_payload = {
            "action": "closed",
            "pull_request": {
                "id": self.pr_global_id,
                "number": self.pr_number,
                "state": "closed",
                "title": "Add hackathon feature",
                "body": "This PR is for the hackathon.",
                "html_url": f"{self.repo_url}/pull/{self.pr_number}",
                "merged": True,
                "created_at": opened_payload["pull_request"]["created_at"],
                "updated_at": merged_at.isoformat().replace("+00:00", "Z"),
                "closed_at": merged_at.isoformat().replace("+00:00", "Z"),
                "merged_at": merged_at.isoformat().replace("+00:00", "Z"),
                "user": {
                    "login": "octocat",
                    "html_url": "https://github.com/octocat",
                    "avatar_url": "https://avatars.githubusercontent.com/u/1?v=4",
                },
            },
            "repository": {
                "full_name": "OWASP-BLT/demo-repo",
                "html_url": self.repo_url,
            },
        }

        response = self._post(closed_payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(GitHubIssue.objects.count(), 1)

        issue = GitHubIssue.objects.get(issue_id=self.pr_global_id, repo=self.repo)
        self.assertEqual(issue.state, "closed")
        self.assertTrue(issue.is_merged)
        self.assertIsNotNone(issue.merged_at)
        self.assertIsNotNone(issue.closed_at)

    def test_invalid_signature_returns_403_and_does_not_create_pr_issue(self):
        """Invalid signature should return 403 and not create any GitHubIssue records."""
        payload = {
            "action": "opened",
            "pull_request": {
                "id": self.pr_global_id,
                "number": self.pr_number,
                "state": "open",
                "title": "Bad sig test",
                "body": "",
                "html_url": f"{self.repo_url}/pull/{self.pr_number}",
                "merged": False,
                "created_at": timezone.now().isoformat(),
                "updated_at": timezone.now().isoformat(),
                "user": {
                    "login": "octocat",
                    "html_url": "https://github.com/octocat",
                    "avatar_url": "https://avatars.githubusercontent.com/u/1?v=4",
                },
            },
            "repository": {
                "full_name": "OWASP-BLT/demo-repo",
                "html_url": self.repo_url,
            },
        }

        # Explicit wrong signature
        response = self._post(payload, signature="sha256=wrong")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(GitHubIssue.objects.count(), 0)

    def test_missing_signature_returns_403(self):
        """Missing signature header should return 403."""
        payload = {
            "action": "opened",
            "pull_request": {
                "id": self.pr_global_id,
                "number": self.pr_number,
                "state": "open",
                "title": "No sig test",
                "body": "",
                "html_url": f"{self.repo_url}/pull/{self.pr_number}",
                "merged": False,
                "created_at": timezone.now().isoformat(),
                "updated_at": timezone.now().isoformat(),
                "user": {
                    "login": "octocat",
                    "html_url": "https://github.com/octocat",
                    "avatar_url": "",
                },
            },
            "repository": {
                "full_name": "OWASP-BLT/demo-repo",
                "html_url": self.repo_url,
            },
        }
        body = json.dumps(payload).encode("utf-8")

        response = self.client.post(
            self.webhook_url,
            data=body,
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="pull_request",
            # Intentionally no HTTP_X_HUB_SIGNATURE_256 header
        )

        self.assertEqual(response.status_code, 403)


@override_settings(GITHUB_WEBHOOK_SECRET="testsecret")
class GitHubWebhookPullRequestIdempotentTestCase(TestCase):
    """Verify that repeated PR events don't duplicate GitHubIssue rows."""

    def setUp(self):
        self.client = Client()
        self.webhook_url = reverse("github-webhook")
        self.secret = "testsecret"

        # Same repo + IDs as the other PR test case
        self.repo_url = "https://github.com/OWASP-BLT/demo-repo"
        self.repo = Repo.objects.create(
            name="demo-repo",
            repo_url=self.repo_url,
            slug="owasp-blt-demo-repo",
        )

        self.pr_global_id = 987654321  # pull_request["id"]
        self.pr_number = 42  # pull_request["number"]

    def _post(self, payload: dict, *, signature=None):
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "HTTP_X_GITHUB_EVENT": "pull_request",
        }
        if signature is None:
            signature = compute_github_signature(self.secret, body)
        headers["HTTP_X_HUB_SIGNATURE_256"] = signature

        return self.client.post(
            self.webhook_url,
            data=body,
            content_type="application/json",
            **headers,
        )

    def test_repeated_events_do_not_duplicate_pr_issue(self):
        """Sending the same 'opened' PR event twice still results in a single GitHubIssue."""
        created_at = timezone.now()
        updated_at = timezone.now()

        payload = {
            "action": "opened",
            "pull_request": {
                "id": self.pr_global_id,
                "number": self.pr_number,
                "state": "open",
                "title": "Idempotency test",
                "body": "",
                "html_url": f"{self.repo_url}/pull/{self.pr_number}",
                "merged": False,
                "created_at": created_at.isoformat().replace("+00:00", "Z"),
                "updated_at": updated_at.isoformat().replace("+00:00", "Z"),
                "user": {
                    "login": "octocat",
                    "html_url": "https://github.com/octocat",
                    "avatar_url": "",
                },
            },
            "repository": {
                "full_name": "OWASP-BLT/demo-repo",
                "html_url": self.repo_url,
            },
        }

        # First event
        response1 = self._post(payload)
        self.assertEqual(response1.status_code, 200)

        # Second identical event
        response2 = self._post(payload)
        self.assertEqual(response2.status_code, 200)

        # Still only one GitHubIssue row for this PR + repo
        self.assertEqual(
            GitHubIssue.objects.filter(issue_id=self.pr_global_id, repo=self.repo).count(),
            1,
        )
