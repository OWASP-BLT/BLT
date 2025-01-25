import json
from unittest.mock import MagicMock, patch

from django.test import TestCase

from website.models import Integration, Organization, SlackIntegration
from website.views.slack_handlers import slack_commands, slack_events


class SlackHandlerTests(TestCase):
    def setUp(self):
        # Create test organization and integration
        self.organization = Organization.objects.create(name="Test Org", url="https://test.org")
        self.integration = Integration.objects.create(
            organization=self.organization, service_name="slack"
        )
        self.slack_integration = SlackIntegration.objects.create(
            integration=self.integration,
            bot_access_token="xoxb-test-token",
            workspace_name="T070JPE5BQQ",  # Test workspace ID
            welcome_message="Welcome {user} to our workspace!",
        )

    @patch("website.views.slack_handlers.verify_slack_signature", return_value=True)
    @patch("website.views.slack_handlers.WebClient")
    def test_team_join_with_custom_message(self, mock_webclient, mock_verify):
        # Mock the Slack client
        mock_client = MagicMock()
        mock_webclient.return_value = mock_client
        mock_client.conversations_open.return_value = {"ok": True, "channel": {"id": "D123"}}
        mock_client.chat_postMessage.return_value = {"ok": True}

        # Create test event data
        event_data = {
            "token": "test-token",
            "team_id": "T070JPE5BQQ",
            "event": {"type": "team_join", "user": {"id": "U123"}},
            "type": "event_callback",
        }

        # Create test request
        request = MagicMock()
        request.body = json.dumps(event_data).encode()
        request.method = "POST"
        request.headers = {
            "X-Slack-Request-Timestamp": "1234567890",
            "X-Slack-Signature": "v0=test",
        }

        # Call the event handler
        response = slack_events(request)

        # Verify DM was opened
        mock_client.conversations_open.assert_called_once_with(users=["U123"])

        # Verify welcome message was sent with custom message
        mock_client.chat_postMessage.assert_called_once()
        call_args = mock_client.chat_postMessage.call_args[1]
        self.assertEqual(call_args["text"], "Welcome {user} to our workspace!")

    @patch("website.views.slack_handlers.verify_slack_signature", return_value=True)
    @patch("website.views.slack_handlers.WebClient")
    def test_team_join_owasp_workspace(self, mock_webclient, mock_verify):
        # Mock the Slack client
        mock_client = MagicMock()
        mock_webclient.return_value = mock_client
        mock_client.conversations_open.return_value = {"ok": True, "channel": {"id": "D123"}}
        mock_client.chat_postMessage.return_value = {"ok": True}

        # Create test event data for OWASP workspace
        event_data = {
            "token": "test-token",
            "team_id": "T04T40NHX",  # OWASP workspace ID
            "event": {"type": "team_join", "user": {"id": "U123"}},
            "type": "event_callback",
        }

        # Create test request
        request = MagicMock()
        request.body = json.dumps(event_data).encode()
        request.method = "POST"
        request.headers = {
            "X-Slack-Request-Timestamp": "1234567890",
            "X-Slack-Signature": "v0=test",
        }

        # Call the event handler
        response = slack_events(request)

        # Verify DM was opened
        mock_client.conversations_open.assert_called_once_with(users=["U123"])

        # Verify default OWASP welcome message was sent
        mock_client.chat_postMessage.assert_called_once()
        call_args = mock_client.chat_postMessage.call_args[1]
        self.assertIn("Welcome to the OWASP Slack Community", call_args["text"])

    @patch("website.views.slack_handlers.verify_slack_signature", return_value=True)
    @patch("website.views.slack_handlers.WebClient")
    def test_slack_command_contrib(self, mock_webclient, mock_verify):
        # Mock the Slack client
        mock_client = MagicMock()
        mock_webclient.return_value = mock_client
        mock_client.conversations_open.return_value = {"ok": True, "channel": {"id": "D123"}}
        mock_client.chat_postMessage.return_value = {"ok": True}

        # Create test request
        request = MagicMock()
        request.method = "POST"
        request.POST = {
            "command": "/contrib",
            "user_id": "U123",
            "team_id": "T070JPE5BQQ",
            "team_domain": "test",
        }
        request.headers = {
            "X-Slack-Request-Timestamp": "1234567890",
            "X-Slack-Signature": "v0=test",
        }

        response = slack_commands(request)

        # Verify DM was opened
        mock_client.conversations_open.assert_called_once_with(users=["U123"])

        # Verify contribute message was sent
        mock_client.chat_postMessage.assert_called_once()
        self.assertEqual(response.status_code, 200)
