"""
Tests for Slack-related management commands.
"""
from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import TestCase

from website.models import Project


class SlackCommandsTests(TestCase):
    """Tests for Slack management commands"""

    def setUp(self):
        """Set up test data"""
        self.project_with_slack = Project.objects.create(
            name="Test Project with Slack",
            slug="test-project-slack",
            description="A test project with Slack",
            slack_channel="project-test",
            slack_id="C12345678",
            slack="https://owasp.slack.com/archives/C12345678",
        )

        self.project_without_slack = Project.objects.create(
            name="Test Project without Slack",
            slug="test-project-no-slack",
            description="A test project without Slack",
        )

    @patch("website.management.commands.update_slack_user_count.requests.get")
    def test_update_slack_user_count_success(self, mock_get):
        """Test successful update of Slack user counts"""
        # Mock Slack API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": True,
            "channel": {
                "id": "C12345678",
                "name": "project-test",
                "num_members": 42,
            },
        }
        mock_get.return_value = mock_response

        out = StringIO()
        call_command("update_slack_user_count", "--slack_token=test-token", stdout=out)

        # Verify the project was updated
        self.project_with_slack.refresh_from_db()
        self.assertEqual(self.project_with_slack.slack_user_count, 42)

        # Verify command output
        output = out.getvalue()
        self.assertIn("Test Project with Slack", output)
        self.assertIn("42 members", output)
        self.assertIn("1 projects updated", output)

    @patch("website.management.commands.update_slack_user_count.requests.get")
    def test_update_slack_user_count_api_error(self, mock_get):
        """Test handling of Slack API errors"""
        # Mock Slack API error response
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": False,
            "error": "channel_not_found",
        }
        mock_get.return_value = mock_response

        out = StringIO()
        call_command("update_slack_user_count", "--slack_token=test-token", stdout=out)

        # Verify the project was not updated (should remain 0)
        self.project_with_slack.refresh_from_db()
        self.assertEqual(self.project_with_slack.slack_user_count, 0)

        # Verify command output shows error
        output = out.getvalue()
        self.assertIn("channel_not_found", output)
        self.assertIn("1 failed", output)

    def test_update_slack_user_count_no_token(self):
        """Test that command fails gracefully without token"""
        out = StringIO()
        with patch("website.management.commands.update_slack_user_count.settings") as mock_settings:
            mock_settings.SLACK_BOT_TOKEN = None
            call_command("update_slack_user_count", stdout=out)

        # Verify error message
        output = out.getvalue()
        self.assertIn("SLACK_BOT_TOKEN not configured", output)

    @patch("website.management.commands.update_slack_user_count.requests.get")
    def test_update_slack_user_count_single_project(self, mock_get):
        """Test updating a single project by ID"""
        # Mock Slack API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": True,
            "channel": {
                "id": "C12345678",
                "name": "project-test",
                "num_members": 15,
            },
        }
        mock_get.return_value = mock_response

        out = StringIO()
        call_command(
            "update_slack_user_count",
            f"--project_id={self.project_with_slack.id}",
            "--slack_token=test-token",
            stdout=out,
        )

        # Verify only the specified project was updated
        self.project_with_slack.refresh_from_db()
        self.assertEqual(self.project_with_slack.slack_user_count, 15)

        # Verify command output
        output = out.getvalue()
        self.assertIn("15 members", output)

    def test_update_slack_user_count_no_projects(self):
        """Test command with no projects having Slack channels"""
        # Remove slack_id from the project
        self.project_with_slack.slack_id = None
        self.project_with_slack.save()

        out = StringIO()
        call_command("update_slack_user_count", "--slack_token=test-token", stdout=out)

        # Verify warning message
        output = out.getvalue()
        self.assertIn("No projects with Slack channels found", output)

    @patch("website.management.commands.update_slack_user_count.requests.get")
    def test_update_slack_user_count_request_exception(self, mock_get):
        """Test handling of request exceptions"""
        # Mock a request exception
        mock_get.side_effect = Exception("Network error")

        out = StringIO()
        call_command("update_slack_user_count", "--slack_token=test-token", stdout=out)

        # Verify the project was not updated
        self.project_with_slack.refresh_from_db()
        self.assertEqual(self.project_with_slack.slack_user_count, 0)

        # Verify command output shows error
        output = out.getvalue()
        self.assertIn("Unexpected error", output)
        self.assertIn("1 failed", output)
