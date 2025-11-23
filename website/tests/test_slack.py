import json
from unittest.mock import MagicMock, patch

from django.test import TestCase

from website.models import Integration, Organization, SlackBotActivity, SlackIntegration
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

    @patch("website.views.slack_handlers.verify_slack_signature", return_value=True)
    @patch("website.views.slack_handlers.WebClient")
    def test_poll_command_help(self, mock_webclient, mock_verify):
        """Test /poll command with no arguments shows help"""
        mock_client = MagicMock()
        mock_webclient.return_value = mock_client
        mock_client.conversations_open.return_value = {"ok": True, "channel": {"id": "D123"}}
        mock_client.chat_postMessage.return_value = {"ok": True}

        # Create test request for /poll with no text
        request = MagicMock()
        request.body = b"command=/poll&user_id=U123&team_id=T070JPE5BQQ&channel_id=C123&text="
        request.method = "POST"
        request.content_type = "application/x-www-form-urlencoded"
        request.POST = {
            "command": "/poll",
            "user_id": "U123",
            "team_id": "T070JPE5BQQ",
            "team_domain": "test-workspace",
            "channel_id": "C123",
            "text": "",
        }
        request.headers = {
            "X-Slack-Request-Timestamp": "1234567890",
            "X-Slack-Signature": "v0=test",
        }

        # Call the command handler
        response = slack_commands(request)

        # Check that help was sent
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn("help", response_data["text"].lower())

    @patch("website.views.slack_handlers.verify_slack_signature", return_value=True)
    @patch("website.views.slack_handlers.WebClient")
    def test_poll_command_create(self, mock_webclient, mock_verify):
        """Test creating a poll with /poll command"""
        from website.models import SlackPoll

        mock_client = MagicMock()
        mock_webclient.return_value = mock_client
        mock_client.chat_postMessage.return_value = {"ok": True, "ts": "1234567890.123456"}

        # Create test request for /poll
        request = MagicMock()
        poll_text = '"What time?" "Morning" "Afternoon" "Evening"'
        request.body = f"command=/poll&user_id=U123&team_id=T070JPE5BQQ&channel_id=C123&text={poll_text}".encode()
        request.method = "POST"
        request.content_type = "application/x-www-form-urlencoded"
        request.POST = {
            "command": "/poll",
            "user_id": "U123",
            "team_id": "T070JPE5BQQ",
            "team_domain": "test-workspace",
            "channel_id": "C123",
            "text": poll_text,
        }
        request.headers = {
            "X-Slack-Request-Timestamp": "1234567890",
            "X-Slack-Signature": "v0=test",
        }

        # Call the command handler
        response = slack_commands(request)

        # Check that poll was created
        self.assertEqual(response.status_code, 200)
        poll = SlackPoll.objects.filter(workspace_id="T070JPE5BQQ").first()
        self.assertIsNotNone(poll)
        self.assertEqual(poll.question, "What time?")
        self.assertEqual(poll.options.count(), 3)
        self.assertEqual(poll.status, "active")

    @patch("website.views.slack_handlers.verify_slack_signature", return_value=True)
    @patch("website.views.slack_handlers.WebClient")
    def test_remind_command_help(self, mock_webclient, mock_verify):
        """Test /remind command with no arguments shows help"""
        mock_client = MagicMock()
        mock_webclient.return_value = mock_client
        mock_client.conversations_open.return_value = {"ok": True, "channel": {"id": "D123"}}
        mock_client.chat_postMessage.return_value = {"ok": True}

        # Create test request for /remind with no text
        request = MagicMock()
        request.body = b"command=/remind&user_id=U123&team_id=T070JPE5BQQ&channel_id=C123&text="
        request.method = "POST"
        request.content_type = "application/x-www-form-urlencoded"
        request.POST = {
            "command": "/remind",
            "user_id": "U123",
            "team_id": "T070JPE5BQQ",
            "team_domain": "test-workspace",
            "channel_id": "C123",
            "text": "",
        }
        request.headers = {
            "X-Slack-Request-Timestamp": "1234567890",
            "X-Slack-Signature": "v0=test",
        }

        # Call the command handler
        response = slack_commands(request)

        # Check that help was sent
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn("help", response_data["text"].lower())

    @patch("website.views.slack_handlers.verify_slack_signature", return_value=True)
    @patch("website.views.slack_handlers.WebClient")
    def test_remind_command_create(self, mock_webclient, mock_verify):
        """Test creating a reminder with /remind command"""
        from website.models import SlackReminder

        mock_client = MagicMock()
        mock_webclient.return_value = mock_client

        # Create test request for /remind
        request = MagicMock()
        remind_text = '"Team meeting" in 30 minutes'
        request.body = f"command=/remind&user_id=U123&team_id=T070JPE5BQQ&channel_id=C123&text={remind_text}".encode()
        request.method = "POST"
        request.content_type = "application/x-www-form-urlencoded"
        request.POST = {
            "command": "/remind",
            "user_id": "U123",
            "team_id": "T070JPE5BQQ",
            "team_domain": "test-workspace",
            "channel_id": "C123",
            "text": remind_text,
        }
        request.headers = {
            "X-Slack-Request-Timestamp": "1234567890",
            "X-Slack-Signature": "v0=test",
        }

        # Call the command handler
        response = slack_commands(request)

        # Check that reminder was created
        self.assertEqual(response.status_code, 200)
        reminder = SlackReminder.objects.filter(workspace_id="T070JPE5BQQ").first()
        self.assertIsNotNone(reminder)
        self.assertEqual(reminder.message, "Team meeting")
        self.assertEqual(reminder.status, "pending")
        self.assertEqual(reminder.target_id, "U123")

    @patch("website.views.slack_handlers.verify_slack_signature", return_value=True)
    @patch("website.views.slack_handlers.WebClient")
    def test_huddle_command_help(self, mock_webclient, mock_verify):
        """Test /huddle command with no arguments shows help"""
        mock_client = MagicMock()
        mock_webclient.return_value = mock_client
        mock_client.conversations_open.return_value = {"ok": True, "channel": {"id": "D123"}}
        mock_client.chat_postMessage.return_value = {"ok": True}

        # Create test request for /huddle with no text
        request = MagicMock()
        request.body = b"command=/huddle&user_id=U123&team_id=T070JPE5BQQ&channel_id=C123&text="
        request.method = "POST"
        request.content_type = "application/x-www-form-urlencoded"
        request.POST = {
            "command": "/huddle",
            "user_id": "U123",
            "team_id": "T070JPE5BQQ",
            "team_domain": "test-workspace",
            "channel_id": "C123",
            "text": "",
        }
        request.headers = {
            "X-Slack-Request-Timestamp": "1234567890",
            "X-Slack-Signature": "v0=test",
        }

        # Call the command handler
        response = slack_commands(request)

        # Check that help was sent
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertIn("help", response_data["text"].lower())

    @patch("website.views.slack_handlers.verify_slack_signature", return_value=True)
    @patch("website.views.slack_handlers.WebClient")
    def test_huddle_command_create(self, mock_webclient, mock_verify):
        """Test creating a huddle with /huddle command"""
        from website.models import SlackHuddle

        mock_client = MagicMock()
        mock_webclient.return_value = mock_client
        mock_client.chat_postMessage.return_value = {"ok": True, "ts": "1234567890.123456"}

        # Create test request for /huddle
        request = MagicMock()
        huddle_text = '"Sprint Planning" "Q1 planning" in 2 hours with <@U456>'
        request.body = f"command=/huddle&user_id=U123&team_id=T070JPE5BQQ&channel_id=C123&text={huddle_text}".encode()
        request.method = "POST"
        request.content_type = "application/x-www-form-urlencoded"
        request.POST = {
            "command": "/huddle",
            "user_id": "U123",
            "team_id": "T070JPE5BQQ",
            "team_domain": "test-workspace",
            "channel_id": "C123",
            "text": huddle_text,
        }
        request.headers = {
            "X-Slack-Request-Timestamp": "1234567890",
            "X-Slack-Signature": "v0=test",
        }

        # Call the command handler
        response = slack_commands(request)

        # Check that huddle was created
        self.assertEqual(response.status_code, 200)
        huddle = SlackHuddle.objects.filter(workspace_id="T070JPE5BQQ").first()
        self.assertIsNotNone(huddle)
        self.assertEqual(huddle.title, "Sprint Planning")
        self.assertEqual(huddle.description, "Q1 planning")
        self.assertEqual(huddle.status, "scheduled")
        self.assertEqual(huddle.participants.count(), 1)
