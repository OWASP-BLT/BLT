import json
from unittest.mock import MagicMock, patch

from django.test import TestCase

from website.management.commands.slack_weekly_report import Command
from website.models import Integration, Organization, Project, SlackBotActivity, SlackIntegration
from website.views.slack_handlers import slack_commands, slack_events


class SlackHandlerTests(TestCase):
    def setUp(self):
        # Create test organization and integration
        self.organization = Organization.objects.create(name="Test Org", url="https://test.org")
        self.integration = Integration.objects.create(organization=self.organization, service_name="slack")
        self.slack_integration = SlackIntegration.objects.create(
            integration=self.integration,
            bot_access_token="xoxb-test-token",
            workspace_name="T070JPE5BQQ",  # Test workspace ID
            welcome_message="Welcome {user} to our workspace!",
        )

    @patch("website.views.slack_handlers.verify_slack_signature", return_value=True)
    @patch("website.views.slack_handlers.WebClient")
    def test_team_join_with_custom_message(self, mock_webclient, mock_verify):
        # Mock the Slack client here
        mock_client = MagicMock()
        mock_webclient.return_value = mock_client
        mock_client.conversations_open.return_value = {"ok": True, "channel": {"id": "D123"}}
        mock_client.chat_postMessage.return_value = {"ok": True}

        # Create test event data
        event_data = {
            "token": "test-token",
            "team_id": "T070JPE5BQQ",  # Using the workspace_name from setUp
            "event": {"type": "team_join", "user": {"id": "U123"}},
            "type": "event_callback",
        }

        # Create test request
        request = MagicMock()
        request.body = json.dumps(event_data).encode()
        request.method = "POST"
        request.content_type = "application/json"
        request.headers = {
            "X-Slack-Request-Timestamp": "1234567890",
            "X-Slack-Signature": "v0=test",
        }

        # Call the event handler
        response = slack_events(request)

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Verify activity was logged
        activity = SlackBotActivity.objects.last()
        self.assertEqual(activity.activity_type, "team_join")
        self.assertEqual(activity.user_id, "U123")
        self.assertEqual(activity.workspace_id, "T070JPE5BQQ")
        self.assertEqual(activity.workspace_name, "Test Org")  # Using organization name from setUp

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
        request.content_type = "application/json"
        request.headers = {
            "X-Slack-Request-Timestamp": "1234567890",
            "X-Slack-Signature": "v0=test",
        }

        # Call the event handler
        response = slack_events(request)

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Verify activity was logged
        activity = SlackBotActivity.objects.last()
        self.assertEqual(activity.activity_type, "team_join")
        self.assertEqual(activity.user_id, "U123")
        self.assertEqual(activity.workspace_id, "T04T40NHX")

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

    @patch("website.views.slack_handlers.verify_slack_signature", return_value=True)
    @patch("website.views.slack_handlers.WebClient")
    def test_slack_command_apps(self, mock_webclient, _mock_verify):
        # Mock the Slack client
        mock_client = MagicMock()
        mock_webclient.return_value = mock_client
        mock_client.conversations_open.return_value = {"ok": True, "channel": {"id": "D123"}}
        mock_client.chat_postMessage.return_value = {"ok": True}
        mock_client.team_info.return_value = {"ok": True, "team": {"name": "Test Workspace"}}

        # Mock admin API response - simulating permission error
        from slack_sdk.errors import SlackApiError

        mock_client.api_call.side_effect = SlackApiError(
            "Insufficient permissions", response={"error": "missing_scope"}
        )

        # Create test request
        request = MagicMock()
        request.method = "POST"
        request.POST = {
            "command": "/apps",
            "user_id": "U123",
            "team_id": "T070JPE5BQQ",
            "team_domain": "test",
        }
        request.headers = {
            "X-Slack-Request-Timestamp": "1234567890",
            "X-Slack-Signature": "v0=test",
        }

        response = slack_commands(request)

        # Verify team info was requested
        mock_client.team_info.assert_called_once()

        # Verify DM was opened
        mock_client.conversations_open.assert_called_once_with(users=["U123"])

        # Verify apps message was sent
        mock_client.chat_postMessage.assert_called_once()

        # Check that the response is correct
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn("apps", response_data["text"].lower())

        # Verify activity was logged
        activity = SlackBotActivity.objects.filter(activity_type="command", user_id="U123").last()
        self.assertIsNotNone(activity)
        self.assertEqual(activity.details["command"], "/apps")


class SlackWeeklyReportTests(TestCase):
    def setUp(self):
        # Create test organization and integration
        self.organization = Organization.objects.create(name="Test Org", url="https://test.org")
        self.integration = Integration.objects.create(organization=self.organization, service_name="slack")
        self.slack_integration = SlackIntegration.objects.create(
            integration=self.integration,
            bot_access_token="xoxb-test-token",
            workspace_name="Test Workspace",
            default_channel_id="C123456",
            default_channel_name="general",
        )

    @patch("slack_bolt.App")
    def test_weekly_report_generation(self, mock_app):
        """Test that weekly report is generated and sent successfully."""
        # Mock the Slack app and client
        mock_client = MagicMock()
        mock_app.return_value.client = mock_client
        mock_client.conversations_join.return_value = None
        mock_client.chat_postMessage.return_value = {"ok": True, "ts": "1234567890.123456"}

        # Run the command
        command = Command()
        command.handle()

        # Verify that the Slack client was called
        mock_app.assert_called_once_with(token="xoxb-test-token")
        mock_client.conversations_join.assert_called_once_with(channel="C123456")
        mock_client.chat_postMessage.assert_called_once()

        # Verify the message content contains expected sections
        call_args = mock_client.chat_postMessage.call_args
        message = call_args.kwargs["text"]
        self.assertIn("Weekly Organization Report", message)
        self.assertIn("Test Org", message)
        self.assertIn("Overview Statistics", message)

    @patch("slack_bolt.App")
    def test_weekly_report_with_projects(self, mock_app):
        """Test weekly report includes project information."""
        # Create a test project
        Project.objects.create(
            organization=self.organization,
            name="Test Project",
            description="A test project",
            status="production",
        )

        # Mock the Slack app and client
        mock_client = MagicMock()
        mock_app.return_value.client = mock_client
        mock_client.conversations_join.return_value = None
        mock_client.chat_postMessage.return_value = {"ok": True, "ts": "1234567890.123456"}

        # Run the command
        command = Command()
        command.handle()

        # Verify the message content includes project info
        call_args = mock_client.chat_postMessage.call_args
        message = call_args.kwargs["text"]
        self.assertIn("Test Project", message)
        self.assertIn("Projects Overview", message)

    @patch("slack_bolt.App")
    def test_weekly_report_custom_channel(self, mock_app):
        """Test that weekly report uses custom channel when configured."""
        # Set custom weekly report channel
        self.slack_integration.weekly_report_channel_id = "C789012"
        self.slack_integration.weekly_report_channel_name = "weekly-reports"
        self.slack_integration.save()

        # Mock the Slack app and client
        mock_client = MagicMock()
        mock_app.return_value.client = mock_client
        mock_client.conversations_join.return_value = None
        mock_client.chat_postMessage.return_value = {"ok": True, "ts": "1234567890.123456"}

        # Run the command
        command = Command()
        command.handle()

        # Verify that the custom channel was used instead of default
        mock_app.assert_called_once_with(token="xoxb-test-token")
        mock_client.conversations_join.assert_called_once_with(channel="C789012")
        mock_client.chat_postMessage.assert_called_once()

        # Verify the message was sent to the custom channel
        call_args = mock_client.chat_postMessage.call_args
        self.assertEqual(call_args.kwargs["channel"], "C789012")

    @patch("slack_bolt.App")
    def test_weekly_report_fallback_to_default_channel(self, mock_app):
        """Test that weekly report falls back to default channel when custom not set."""
        # Ensure weekly report channel is not set (it's None by default in setUp)
        self.assertIsNone(self.slack_integration.weekly_report_channel_id)

        # Mock the Slack app and client
        mock_client = MagicMock()
        mock_app.return_value.client = mock_client
        mock_client.conversations_join.return_value = None
        mock_client.chat_postMessage.return_value = {"ok": True, "ts": "1234567890.123456"}

        # Run the command
        command = Command()
        command.handle()

        # Verify that the default channel was used
        mock_app.assert_called_once_with(token="xoxb-test-token")
        mock_client.conversations_join.assert_called_once_with(channel="C123456")
        mock_client.chat_postMessage.assert_called_once()

        # Verify the message was sent to the default channel
        call_args = mock_client.chat_postMessage.call_args
        self.assertEqual(call_args.kwargs["channel"], "C123456")
