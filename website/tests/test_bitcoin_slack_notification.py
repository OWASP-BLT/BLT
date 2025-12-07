import json
import re
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from website.models import BaconSubmission, Integration, Organization, SlackIntegration


class BaconSubmissionSlackNotificationTests(TestCase):
    """Tests for Slack notification functionality in BaconSubmissionView"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.client.login(email="test@example.com", password="testpass123")

        # Create OWASP BLT organization
        self.organization = Organization.objects.create(
            name="OWASP BLT",
            url="https://owaspblt.org",
        )

        # Create Slack integration
        self.integration = Integration.objects.create(
            organization=self.organization,
            service_name="slack",
        )

        self.slack_integration = SlackIntegration.objects.create(
            integration=self.integration,
            bot_access_token="xoxb-test-token",
            default_channel_id="C1234567890",
        )

    @patch("website.views.bitcoin.WebClient")
    def test_slack_notification_sent_on_submission(self, mock_webclient_class):
        """Test that Slack notification is sent when submission is created"""
        # Mock Slack WebClient
        mock_client = MagicMock()
        mock_webclient_class.return_value = mock_client
        mock_client.chat_postMessage.return_value = {"ok": True}

        # Create submission
        data = {
            "github_url": "https://github.com/OWASP-BLT/BLT/pull/123",
            "contribution_type": "security",
            "description": "Fixed a security vulnerability",
            "bacon_amount": 100,
            "status": "in_review",
        }

        response = self.client.post(
            reverse("bacon_submit"),
            data=json.dumps(data),
            content_type="application/json",
        )

        # Verify submission was created
        self.assertEqual(response.status_code, 201)
        submission = BaconSubmission.objects.first()
        self.assertIsNotNone(submission)
        self.assertEqual(submission.user, self.user)

        # Verify Slack notification was sent
        mock_client.chat_postMessage.assert_called_once()
        call_args = mock_client.chat_postMessage.call_args
        self.assertEqual(call_args.kwargs["channel"], "C1234567890")
        self.assertIn("New BACON Claim Submitted", call_args.kwargs["text"])
        self.assertIn("testuser", call_args.kwargs["text"])
        self.assertIn("security", call_args.kwargs["text"])
        self.assertIn("https://github.com/OWASP-BLT/BLT/pull/123", call_args.kwargs["text"])

    @patch("website.views.bitcoin.WebClient")
    def test_slack_notification_finds_channel_dynamically(self, mock_webclient_class):
        """Test that Slack notification finds channel if default_channel_id is not set"""
        # Remove default channel ID
        self.slack_integration.default_channel_id = None
        self.slack_integration.save()

        # Mock Slack WebClient
        mock_client = MagicMock()
        mock_webclient_class.return_value = mock_client
        mock_client.conversations_list.return_value = {
            "ok": True,
            "channels": [
                {"id": "C111", "name": "general"},
                {"id": "C222", "name": "project-blt-bacon"},
                {"id": "C333", "name": "other"},
            ],
            "response_metadata": {"next_cursor": ""},
        }
        mock_client.chat_postMessage.return_value = {"ok": True}

        # Create submission
        data = {
            "github_url": "https://github.com/OWASP-BLT/BLT/pull/123",
            "contribution_type": "security",
            "description": "Fixed a security vulnerability",
            "bacon_amount": 100,
            "status": "in_review",
        }

        response = self.client.post(
            reverse("bacon_submit"),
            data=json.dumps(data),
            content_type="application/json",
        )

        # Verify submission was created
        self.assertEqual(response.status_code, 201)

        # Verify channel lookup was called
        mock_client.conversations_list.assert_called_once()
        # Verify notification was sent to found channel
        mock_client.chat_postMessage.assert_called_once()
        call_args = mock_client.chat_postMessage.call_args
        self.assertEqual(call_args.kwargs["channel"], "C222")

    @patch("website.views.bitcoin.WebClient")
    def test_slack_notification_handles_pagination(self, mock_webclient_class):
        """Test that Slack notification handles pagination when searching for channel"""
        # Remove default channel ID
        self.slack_integration.default_channel_id = None
        self.slack_integration.save()

        # Mock Slack WebClient with pagination
        mock_client = MagicMock()
        mock_webclient_class.return_value = mock_client
        mock_client.conversations_list.side_effect = [
            {
                "ok": True,
                "channels": [{"id": "C111", "name": "general"}],
                "response_metadata": {"next_cursor": "cursor123"},
            },
            {
                "ok": True,
                "channels": [{"id": "C222", "name": "project-blt-bacon"}],
                "response_metadata": {"next_cursor": ""},
            },
        ]
        mock_client.chat_postMessage.return_value = {"ok": True}

        # Create submission
        data = {
            "github_url": "https://github.com/OWASP-BLT/BLT/pull/123",
            "contribution_type": "security",
            "description": "Fixed a security vulnerability",
            "bacon_amount": 100,
            "status": "in_review",
        }

        response = self.client.post(
            reverse("bacon_submit"),
            data=json.dumps(data),
            content_type="application/json",
        )

        # Verify submission was created
        self.assertEqual(response.status_code, 201)

        # Verify pagination was handled (called twice)
        self.assertEqual(mock_client.conversations_list.call_count, 2)
        # Verify notification was sent to found channel
        mock_client.chat_postMessage.assert_called_once()
        call_args = mock_client.chat_postMessage.call_args
        self.assertEqual(call_args.kwargs["channel"], "C222")

    @patch("website.views.bitcoin.WebClient")
    def test_slack_notification_channel_not_found(self, mock_webclient_class):
        """Test that submission succeeds when #project-blt-bacon channel doesn't exist"""
        # Remove default channel ID
        self.slack_integration.default_channel_id = None
        self.slack_integration.save()

        # Mock Slack WebClient - channel not found in any page (tests pagination)
        mock_client = MagicMock()
        mock_webclient_class.return_value = mock_client
        # Use side_effect with enough responses to test pagination, but return empty cursor on final call
        mock_client.conversations_list.side_effect = [
            {
                "ok": True,
                "channels": [{"id": "C111", "name": "general"}, {"id": "C222", "name": "other"}],
                "response_metadata": {"next_cursor": "cursor123"},
            },
            {
                "ok": True,
                "channels": [{"id": "C333", "name": "random"}],
                "response_metadata": {"next_cursor": ""},  # Empty cursor stops pagination
            },
        ]

        # Create submission
        data = {
            "github_url": "https://github.com/OWASP-BLT/BLT/pull/123",
            "contribution_type": "security",
            "description": "Fixed a security vulnerability",
            "bacon_amount": 100,
            "status": "in_review",
        }

        response = self.client.post(
            reverse("bacon_submit"),
            data=json.dumps(data),
            content_type="application/json",
        )

        # Verify submission was created successfully
        self.assertEqual(response.status_code, 201)
        submission = BaconSubmission.objects.first()
        self.assertIsNotNone(submission)

        # Verify channel lookup was attempted (pagination handled - called twice)
        self.assertEqual(mock_client.conversations_list.call_count, 2)
        # Verify chat_postMessage was never called since channel wasn't found
        mock_client.chat_postMessage.assert_not_called()

    def test_submission_succeeds_when_slack_fails(self):
        """Test that submission creation succeeds even if Slack notification fails"""
        # Remove Slack integration to simulate failure
        self.slack_integration.delete()

        # Create submission
        data = {
            "github_url": "https://github.com/OWASP-BLT/BLT/pull/123",
            "contribution_type": "security",
            "description": "Fixed a security vulnerability",
            "bacon_amount": 100,
            "status": "in_review",
        }

        response = self.client.post(
            reverse("bacon_submit"),
            data=json.dumps(data),
            content_type="application/json",
        )

        # Verify submission was created successfully despite Slack failure
        self.assertEqual(response.status_code, 201)
        submission = BaconSubmission.objects.first()
        self.assertIsNotNone(submission)

    @patch("website.views.bitcoin.WebClient")
    def test_slack_notification_sanitizes_description(self, mock_webclient_class):
        """Test that description is properly sanitized for Slack markdown"""
        mock_client = MagicMock()
        mock_webclient_class.return_value = mock_client
        mock_client.chat_postMessage.return_value = {"ok": True}

        # Create submission with special characters in description
        data = {
            "github_url": "https://github.com/OWASP-BLT/BLT/pull/123",
            "contribution_type": "security",
            "description": "Test with *markdown* _formatting_ `code` <script>alert('xss')</script> & entities",
            "bacon_amount": 100,
            "status": "in_review",
        }

        response = self.client.post(
            reverse("bacon_submit"),
            data=json.dumps(data),
            content_type="application/json",
        )

        # Verify submission was created
        self.assertEqual(response.status_code, 201)

        # Verify description was sanitized in Slack message
        mock_client.chat_postMessage.assert_called_once()
        call_args = mock_client.chat_postMessage.call_args
        message_text = call_args.kwargs["text"]
        # Check that special characters are escaped
        self.assertIn("\\*markdown\\*", message_text)
        self.assertIn("\\_formatting\\_", message_text)
        self.assertIn("\\`code\\`", message_text)
        self.assertIn("&lt;script&gt;", message_text)
        self.assertIn("&amp; entities", message_text)

    @patch("website.views.bitcoin.WebClient")
    def test_slack_notification_truncates_long_description(self, mock_webclient_class):
        """Test that long descriptions are truncated to 200 characters"""
        mock_client = MagicMock()
        mock_webclient_class.return_value = mock_client
        mock_client.chat_postMessage.return_value = {"ok": True}

        # Create submission with very long description
        long_description = "A" * 300
        data = {
            "github_url": "https://github.com/OWASP-BLT/BLT/pull/123",
            "contribution_type": "security",
            "description": long_description,
            "bacon_amount": 100,
            "status": "in_review",
        }

        response = self.client.post(
            reverse("bacon_submit"),
            data=json.dumps(data),
            content_type="application/json",
        )

        # Verify submission was created
        self.assertEqual(response.status_code, 201)

        # Verify description was truncated in Slack message
        mock_client.chat_postMessage.assert_called_once()
        call_args = mock_client.chat_postMessage.call_args
        message_text = call_args.kwargs["text"]
        # Check that description ends with "..."
        self.assertIn("...", message_text)
        # Extract description part and verify length
        # Note: Slack API may use literal backslash-n sequences ("\\n") in the message
        desc_start = message_text.find("*Description:*") + len("*Description:*")
        # Try literal backslash-n first (as per production behavior), fallback to actual newline
        desc_end = message_text.find("\\n", desc_start)
        if desc_end == -1:
            # Fallback to actual newline character if literal not found
            desc_end = message_text.find("\n", desc_start)
        if desc_end == -1:
            desc_end = len(message_text)
        description_part = message_text[desc_start:desc_end].strip()
        # Should be 200 chars + "..." = 203 chars max
        self.assertLessEqual(len(description_part), 203)

    @patch("website.views.bitcoin.WebClient")
    def test_slack_notification_includes_all_fields(self, mock_webclient_class):
        """Test that Slack notification includes all required fields"""
        mock_client = MagicMock()
        mock_webclient_class.return_value = mock_client
        mock_client.chat_postMessage.return_value = {"ok": True}

        data = {
            "github_url": "https://github.com/OWASP-BLT/BLT/pull/456",
            "contribution_type": "non-security",
            "description": "Added new feature",
            "bacon_amount": 50,
            "status": "accepted",
        }

        response = self.client.post(
            reverse("bacon_submit"),
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)

        # Verify all fields are in the message
        mock_client.chat_postMessage.assert_called_once()
        call_args = mock_client.chat_postMessage.call_args
        message_text = call_args.kwargs["text"]

        self.assertIn("testuser", message_text)  # Username
        self.assertIn("non-security", message_text)  # Type
        self.assertIn("https://github.com/OWASP-BLT/BLT/pull/456", message_text)  # PR link
        self.assertIn("Added new feature", message_text)  # Description
        self.assertIn("50 BACON", message_text)  # Amount
        self.assertIn("accepted", message_text)  # Status

    @patch("website.views.bitcoin.WebClient")
    def test_slack_notification_escapes_username_markdown(self, mock_webclient_class):
        """Test that username with Slack markdown characters is properly escaped"""
        # Create user with markdown characters in username
        user_with_markdown = User.objects.create_user(
            username="user_with_*bold*_underscore_`code`",
            password="testpass123",
        )
        self.client.login(email=user_with_markdown.email, password="testpass123")

        mock_client = MagicMock()
        mock_webclient_class.return_value = mock_client
        mock_client.chat_postMessage.return_value = {"ok": True}

        data = {
            "github_url": "https://github.com/OWASP-BLT/BLT/pull/123",
            "contribution_type": "security",
            "description": "Test description",
            "bacon_amount": 100,
            "status": "in_review",
        }

        response = self.client.post(
            reverse("bacon_submit"),
            data=json.dumps(data),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 201)

        # Verify username was escaped in Slack message
        mock_client.chat_postMessage.assert_called_once()
        call_args = mock_client.chat_postMessage.call_args
        message_text = call_args.kwargs["text"]

        # Check that markdown characters are escaped
        self.assertIn("\\*bold\\*", message_text)
        self.assertIn("\\_underscore\\_", message_text)
        self.assertIn("\\`code\\`", message_text)
        # Verify original unescaped version is NOT present (use regex to check for unescaped markdown)
        # Negative lookbehind ensures the markdown is not preceded by a backslash
        unescaped_bold_pattern = r"(?<!\\)\*bold\*"
        unescaped_underscore_pattern = r"(?<!\\)_underscore_"
        self.assertIsNone(
            re.search(unescaped_bold_pattern, message_text),
            "Unescaped *bold* should not appear in message",
        )
        self.assertIsNone(
            re.search(unescaped_underscore_pattern, message_text),
            "Unescaped _underscore_ should not appear in message",
        )

    @patch("website.views.bitcoin.WebClient")
    def test_slack_api_error_does_not_fail_submission(self, mock_webclient_class):
        """Test that Slack API errors don't prevent submission creation"""
        from slack_sdk.errors import SlackApiError

        mock_client = MagicMock()
        mock_webclient_class.return_value = mock_client
        # Simulate Slack API error
        mock_client.chat_postMessage.side_effect = SlackApiError(
            "Invalid channel", response={"error": "channel_not_found"}
        )

        data = {
            "github_url": "https://github.com/OWASP-BLT/BLT/pull/123",
            "contribution_type": "security",
            "description": "Fixed a security vulnerability",
            "bacon_amount": 100,
            "status": "in_review",
        }

        response = self.client.post(
            reverse("bacon_submit"),
            data=json.dumps(data),
            content_type="application/json",
        )

        # Verify submission was created despite Slack error
        self.assertEqual(response.status_code, 201)
        submission = BaconSubmission.objects.first()
        self.assertIsNotNone(submission)
