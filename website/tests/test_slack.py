import json
from unittest.mock import MagicMock, patch

from django.test import TestCase

from website.management.commands.slack_weekly_report import Command
from website.models import Integration, Organization, Project, SlackBotActivity, SlackIntegration
from website.views.slack_handlers import get_project_with_least_members, slack_commands, slack_events


class GetProjectWithLeastMembersTests(TestCase):
    def setUp(self):
        """Set up test data for project tests."""
        self.organization = Organization.objects.create(name="Test Org", url="https://test.org")

    def test_returns_project_with_least_members(self):
        """Test that it returns the project with the least members."""
        Project.objects.create(
            organization=self.organization,
            name="Project A",
            slug="project-a",
            description="Test project A",
            slack_channel="project-a",
            slack_user_count=50,
        )
        Project.objects.create(
            organization=self.organization,
            name="Project B",
            slug="project-b",
            description="Test project B",
            slack_channel="project-b",
            slack_user_count=10,
        )
        Project.objects.create(
            organization=self.organization,
            name="Project C",
            slug="project-c",
            description="Test project C",
            slack_channel="project-c",
            slack_user_count=30,
        )

        result = get_project_with_least_members()
        self.assertEqual(result, "project-b")

    def test_excludes_project_blt(self):
        """Test that project-blt is excluded from results."""
        Project.objects.create(
            organization=self.organization,
            name="BLT Project",
            slug="blt-project",
            description="BLT project",
            slack_channel="project-blt",
            slack_user_count=5,
        )
        Project.objects.create(
            organization=self.organization,
            name="Other Project",
            slug="other-project",
            description="Other project",
            slack_channel="project-other",
            slack_user_count=20,
        )

        result = get_project_with_least_members()
        self.assertEqual(result, "project-other")

    def test_returns_none_when_no_eligible_projects(self):
        """Test that None is returned when no eligible projects exist."""
        # Create only project-blt which should be excluded
        Project.objects.create(
            organization=self.organization,
            name="BLT Project",
            slug="blt-project",
            description="BLT project",
            slack_channel="project-blt",
            slack_user_count=5,
        )

        result = get_project_with_least_members()
        self.assertIsNone(result)

    def test_filters_out_null_slack_channel(self):
        """Test that projects with null slack_channel are filtered out."""
        Project.objects.create(
            organization=self.organization,
            name="No Channel",
            slug="no-channel",
            description="No channel project",
            slack_channel=None,
            slack_user_count=5,
        )
        Project.objects.create(
            organization=self.organization,
            name="With Channel",
            slug="with-channel",
            description="With channel project",
            slack_channel="project-with-channel",
            slack_user_count=20,
        )

        result = get_project_with_least_members()
        self.assertEqual(result, "project-with-channel")

    def test_filters_out_zero_user_count(self):
        """Test that projects with slack_user_count=0 are filtered out."""
        Project.objects.create(
            organization=self.organization,
            name="Zero Users",
            slug="zero-users",
            description="Zero users project",
            slack_channel="project-zero",
            slack_user_count=0,
        )
        Project.objects.create(
            organization=self.organization,
            name="Some Users",
            slug="some-users",
            description="Some users project",
            slack_channel="project-some",
            slack_user_count=15,
        )

        result = get_project_with_least_members()
        self.assertEqual(result, "project-some")


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
        mock_client.users_info.return_value = {
            "ok": True,
            "user": {"id": "U123", "name": "testuser", "real_name": "Test User"},
        }

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
        mock_client.users_info.return_value = {
            "ok": True,
            "user": {"id": "U123", "name": "testuser", "real_name": "Test User"},
        }

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
        mock_client.users_info.return_value = {
            "ok": True,
            "user": {"id": "U123", "name": "testuser", "real_name": "Test User"},
        }

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
        mock_client.users_info.return_value = {
            "ok": True,
            "user": {"id": "U123", "name": "testuser", "real_name": "Test User"},
        }

        # Mock admin API response - simulating permission error
        from slack_sdk.errors import SlackApiError

        mock_client.api_call.side_effect = SlackApiError(
            "Insufficient permissions", response={"error": "missing_scope"}
        )

        # Create test request
        request = MagicMock()
        request.method = "POST"
        request.POST = {
            "command": "/installed_apps",
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
        self.assertEqual(activity.details["command"], "/installed_apps")


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

    @patch("website.management.commands.slack_weekly_report.App")
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

    @patch("website.management.commands.slack_weekly_report.App")
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

    @patch("website.management.commands.slack_weekly_report.App")
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

    @patch("website.management.commands.slack_weekly_report.App")
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
