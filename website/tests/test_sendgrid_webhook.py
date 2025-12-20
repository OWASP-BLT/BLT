import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from website.models import Domain, UserProfile


class SendGridWebhookTestCase(TestCase):
    """Test SendGrid webhook handling and Slack notification"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.webhook_url = reverse("inbound_event_webhook_callback")

        # Create test user with email
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass")
        self.user_profile = UserProfile.objects.get(user=self.user)

        # Create test domain
        self.domain = Domain.objects.create(
            name="example.com",
            url="https://example.com",
            email="test@example.com",
        )

    @patch("website.views.organization.requests.post")
    def test_webhook_sends_to_slack_with_bounce_event(self, mock_post):
        """Test that webhook sends bounce event to Slack"""
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None

        payload = [
            {
                "email": "test@example.com",
                "event": "bounce",
                "reason": "Invalid mailbox",
                "timestamp": "2024-01-01 12:00:00",
                "sg_message_id": "test-message-id",
            }
        ]

        with patch.dict("os.environ", {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}):
            response = self.client.post(
                self.webhook_url,
                data=json.dumps(payload),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["detail"], "Inbound Sendgrid Webhook received")

        # Verify Slack webhook was called
        self.assertTrue(mock_post.called)
        call_args = mock_post.call_args
        self.assertEqual(call_args[0][0], "https://hooks.slack.com/test")

        # Verify the payload sent to Slack
        slack_payload = call_args[1]["json"]
        self.assertIn("blocks", slack_payload)
        self.assertEqual(len(slack_payload["blocks"]), 1)

        # Verify the message contains event details
        text = slack_payload["blocks"][0]["text"]["text"]
        self.assertIn("BOUNCE", text)
        self.assertIn("test@example.com", text)
        self.assertIn("Invalid mailbox", text)

    @patch("website.views.organization.requests.post")
    def test_webhook_sends_to_slack_with_click_event(self, mock_post):
        """Test that webhook sends click event to Slack"""
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None

        payload = [
            {
                "email": "test@example.com",
                "event": "click",
                "url": "https://example.com/link",
                "timestamp": "2024-01-01 12:00:00",
            }
        ]

        with patch.dict("os.environ", {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}):
            response = self.client.post(
                self.webhook_url,
                data=json.dumps(payload),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)

        # Verify Slack webhook was called
        self.assertTrue(mock_post.called)
        slack_payload = mock_post.call_args[1]["json"]
        text = slack_payload["blocks"][0]["text"]["text"]
        self.assertIn("CLICK", text)
        self.assertIn("https://example.com/link", text)

    @patch("website.views.organization.logger")
    def test_webhook_without_slack_url_logs_debug(self, mock_logger):
        """Test that webhook logs debug message when SLACK_WEBHOOK_URL is not set"""
        payload = [
            {
                "email": "test@example.com",
                "event": "open",
                "timestamp": "2024-01-01 12:00:00",
            }
        ]

        with patch.dict("os.environ", {}, clear=True):
            response = self.client.post(
                self.webhook_url,
                data=json.dumps(payload),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)

        # Verify debug log was called
        mock_logger.debug.assert_called_with("SLACK_WEBHOOK_URL not configured, skipping Slack notification")

    @patch("website.views.organization.requests.post")
    @patch("website.views.organization.logger")
    def test_webhook_handles_slack_error_gracefully(self, mock_logger, mock_post):
        """Test that webhook handles Slack errors without failing the webhook"""
        # Simulate Slack webhook error
        mock_post.side_effect = Exception("Slack is down")

        payload = [
            {
                "email": "test@example.com",
                "event": "delivered",
                "timestamp": "2024-01-01 12:00:00",
            }
        ]

        with patch.dict("os.environ", {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}):
            response = self.client.post(
                self.webhook_url,
                data=json.dumps(payload),
                content_type="application/json",
            )

        # Webhook should still succeed even if Slack fails
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["detail"], "Inbound Sendgrid Webhook received")

        # Verify error was logged
        mock_logger.error.assert_called()

    @patch("website.views.organization.requests.post")
    def test_webhook_sends_multiple_events_to_slack(self, mock_post):
        """Test that webhook sends multiple events to Slack"""
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = lambda: None

        payload = [
            {
                "email": "test1@example.com",
                "event": "delivered",
                "timestamp": "2024-01-01 12:00:00",
            },
            {
                "email": "test2@example.com",
                "event": "open",
                "timestamp": "2024-01-01 12:05:00",
            },
        ]

        with patch.dict("os.environ", {"SLACK_WEBHOOK_URL": "https://hooks.slack.com/test"}):
            response = self.client.post(
                self.webhook_url,
                data=json.dumps(payload),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)

        # Verify Slack webhook was called twice (once for each event)
        self.assertEqual(mock_post.call_count, 2)

    def test_webhook_updates_user_profile(self):
        """Test that webhook still updates user profile as before"""
        payload = [
            {
                "email": "test@example.com",
                "event": "bounce",
                "reason": "Invalid mailbox",
                "timestamp": "2024-01-01 12:00:00",
            }
        ]

        with patch.dict("os.environ", {}, clear=True):
            response = self.client.post(
                self.webhook_url,
                data=json.dumps(payload),
                content_type="application/json",
            )

        self.assertEqual(response.status_code, 200)

        # Verify user profile was updated
        self.user_profile.refresh_from_db()
        self.assertEqual(self.user_profile.email_status, "bounce")
        self.assertEqual(self.user_profile.email_last_event, "bounce")
        self.assertEqual(self.user_profile.email_bounce_reason, "Invalid mailbox")
