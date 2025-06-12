import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse


@override_settings(GITHUB_AIBOT_WEBHOOK_SECRET="test_secret")
@override_settings(LOGGING={"version": 1, "disable_existing_loggers": True})
class MainGitHubWebhookDispatcherTests(TestCase):
    def setUp(self):
        self.url = reverse("main_github_aibot_webhook_dispatcher")
        self.valid_headers = {
            "X-GitHub-Event": "ping",
            "X-Hub-Signature-256": "sha256=valid_signature",
            "Content-Type": "application/json",
        }
        self.valid_body = json.dumps({"zen": "Test message"})

    def test_invalid_http_method(self):
        """Test GET request rejection (non POST request) )"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 400)
        self.assertIn("Only POST requests", response.content.decode())

    def test_missing_signature(self):
        """Test signature verification"""
        response = self.client.post(
            self.url, data=self.valid_body, headers={"X-GitHub-Event": "ping"}, content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Missing webhook signature header", response.json()["error"])

    def test_invalid_signature(self):
        """Test invalid signature handling"""
        invalid_headers = self.valid_headers.copy()
        invalid_headers["X-Hub-Signature-256"] = "sha256=invalid_signature"
        response = self.client.post(
            self.url, data=self.valid_body, headers=invalid_headers, content_type="application/json"
        )
        self.assertEqual(response.status_code, 403)
        self.assertIn("Invalid webhook signature", response.json()["error"])

    def test_empty_request_body(self):
        """Test empty request body handling"""
        response = self.client.post(self.url, data="", headers=self.valid_headers, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Empty request body", response.json()["error"])

    def test_invalid_json(self):
        """Test malformed JSON handling"""
        response = self.client.post(
            self.url, data="INVALID_JSON", headers=self.valid_headers, content_type="application/json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid JSON payload", response.json()["error"])

    @patch("website.views.aibot.verify_github_signature", return_value=True)
    def test_missing_event_header(self, mock_verify_signature):
        """Test missing event header handling"""
        headers = self.valid_headers.copy()
        del headers["X-GitHub-Event"]
        response = self.client.post(self.url, data=self.valid_body, headers=headers, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing X-GitHub-Event header", response.json()["error"])

    @patch("website.views.aibot.verify_github_signature", return_value=True)
    def test_valid_ping_event(self, mock_verify_signature):
        """Test path for ping event"""
        response = self.client.post(
            self.url, data=self.valid_body, headers=self.valid_headers, content_type="application/json"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "pong", "zen": "Test message"})

    @patch("website.views.aibot.verify_github_signature", return_value=True)
    @patch("website.views.aibot.handle_pull_request_event", side_effect=Exception("Test message"))
    def test_generic_error_during_event_handling(self, mock_handler, mock_verify_signature):
        """Test path for a generic error raised during event handling"""
        headers = self.valid_headers.copy()
        headers["X-GitHub-Event"] = "pull_request"
        response = self.client.post(self.url, data=self.valid_body, headers=headers, content_type="application/json")
        self.assertEqual(response.status_code, 500)
        self.assertIn("Unexpected error", response.json()["error"])

    @patch("website.views.aibot.verify_github_signature", return_value=True)
    @patch("website.views.aibot.handle_pull_request_event")
    def test_valid_pull_request_event(self, mock_handler, mock_verify_signature):
        """Test path for pull request event"""
        headers = self.valid_headers.copy()
        headers["X-GitHub-Event"] = "pull_request"
        response = self.client.post(self.url, data=self.valid_body, headers=headers, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        mock_handler.assert_called_once()
        self.assertIn("Pull request event processed", response.json()["status"])

    @patch("website.views.aibot.verify_github_signature", return_value=True)
    @patch("website.views.aibot.handle_comment_event")
    def test_valid_comment_event(self, mock_handler, mock_verify_signature):
        """Test path for issue comment event"""
        headers = self.valid_headers.copy()
        headers["X-GitHub-Event"] = "issue_comment"
        response = self.client.post(self.url, data=self.valid_body, headers=headers, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        mock_handler.assert_called_once()
        self.assertIn("Comment event processed", response.json()["status"])

    @patch("website.views.aibot.verify_github_signature", return_value=True)
    @patch("website.views.aibot.handle_issue_event")
    def test_valid_issue_event(self, mock_handler, mock_verify_signature):
        """Test path for issue event"""
        headers = self.valid_headers.copy()
        headers["X-GitHub-Event"] = "issues"
        response = self.client.post(self.url, data=self.valid_body, headers=headers, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        mock_handler.assert_called_once()
        self.assertIn("Issue event processed", response.json()["status"])
