"""
Tests for Slack-related management commands.
"""

from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import TestCase

from website.models import Project, SlackChannel


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
        # Mock Slack API response for conversations.members
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": True,
            "members": ["U1", "U2", "U3"] * 14,  # 42 members
            "response_metadata": {"next_cursor": ""},
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
        with patch.dict("os.environ", {}, clear=True):
            call_command("update_slack_user_count", stdout=out)

        # Verify error message
        output = out.getvalue()
        self.assertIn("SLACK_BOT_TOKEN not configured", output)

    @patch("website.management.commands.update_slack_user_count.requests.get")
    def test_update_slack_user_count_single_project(self, mock_get):
        """Test updating a single project by ID"""
        # Mock Slack API response for conversations.members
        mock_response = Mock()
        mock_response.json.return_value = {
            "ok": True,
            "members": ["U1", "U2", "U3", "U4", "U5"] * 3,  # 15 members
            "response_metadata": {"next_cursor": ""},
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
        # Remove both slack_id and slack_channel from the project
        self.project_with_slack.slack_id = None
        self.project_with_slack.slack_channel = None
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

    @patch("website.management.commands.update_slack_user_count.requests.get")
    def test_update_slack_user_count_pagination(self, mock_get):
        """Test pagination support for channels with many members"""
        # Mock Slack API responses with pagination
        mock_response1 = Mock()
        mock_response1.json.return_value = {
            "ok": True,
            "members": ["U1", "U2", "U3", "U4", "U5"],  # 5 members in first page
            "response_metadata": {"next_cursor": "cursor123"},
        }
        mock_response2 = Mock()
        mock_response2.json.return_value = {
            "ok": True,
            "members": ["U6", "U7", "U8"],  # 3 members in second page
            "response_metadata": {"next_cursor": ""},  # No more pages
        }
        mock_get.side_effect = [mock_response1, mock_response2]

        out = StringIO()
        call_command("update_slack_user_count", "--slack_token=test-token", stdout=out)

        # Verify the project was updated with total from both pages
        self.project_with_slack.refresh_from_db()
        self.assertEqual(self.project_with_slack.slack_user_count, 8)

        # Verify command output
        output = out.getvalue()
        self.assertIn("8 members", output)
        self.assertIn("1 projects updated", output)

    @patch("website.management.commands.update_slack_user_count.requests.get")
    def test_resolve_channel_from_name(self, mock_get):
        """Test resolving channel ID from channel name when slack_id is missing"""
        # Delete the existing project_with_slack to test in isolation
        self.project_with_slack.delete()

        # Create a project with only slack_channel (no slack_id or slack URL)
        project_channel_only = Project.objects.create(
            name="Project Channel Only",
            slug="project-channel-only",
            description="A project with only slack channel name",
            slack_channel="project-channel-only",
        )

        # Mock responses: first for conversations.list, then for conversations.members
        mock_channels_response = Mock()
        mock_channels_response.json.return_value = {
            "ok": True,
            "channels": [
                {"name": "project-channel-only", "id": "C98765432"},
                {"name": "other-channel", "id": "C11111111"},
            ],
            "response_metadata": {"next_cursor": ""},
        }
        mock_members_response = Mock()
        mock_members_response.json.return_value = {
            "ok": True,
            "members": ["U1", "U2", "U3", "U4", "U5"],  # 5 members
            "response_metadata": {"next_cursor": ""},
        }

        mock_get.side_effect = [mock_channels_response, mock_members_response]

        out = StringIO()
        call_command("update_slack_user_count", "--slack_token=test-token", stdout=out)

        # Verify the project was resolved and updated
        project_channel_only.refresh_from_db()
        self.assertEqual(project_channel_only.slack_id, "C98765432")
        self.assertEqual(project_channel_only.slack, "https://owasp.slack.com/archives/C98765432")
        self.assertEqual(project_channel_only.slack_user_count, 5)

        # Verify command output
        output = out.getvalue()
        self.assertIn("Resolved channel for Project Channel Only", output)
        self.assertIn("1 channels resolved", output)

    @patch("website.management.commands.update_slack_user_count.requests.get")
    def test_resolve_channel_with_hash_prefix(self, mock_get):
        """Test resolving channel ID when slack_channel has # prefix"""
        # Delete the existing project_with_slack to test in isolation
        self.project_with_slack.delete()

        # Create a project with slack_channel that has # prefix
        project_with_hash = Project.objects.create(
            name="Project With Hash",
            slug="project-with-hash",
            description="A project with # prefixed channel name",
            slack_channel="#project-hash-channel",
        )

        # Mock responses
        mock_channels_response = Mock()
        mock_channels_response.json.return_value = {
            "ok": True,
            "channels": [
                {"name": "project-hash-channel", "id": "C87654321"},
            ],
            "response_metadata": {"next_cursor": ""},
        }
        mock_members_response = Mock()
        mock_members_response.json.return_value = {
            "ok": True,
            "members": ["U1", "U2", "U3"],  # 3 members
            "response_metadata": {"next_cursor": ""},
        }

        mock_get.side_effect = [mock_channels_response, mock_members_response]

        out = StringIO()
        call_command("update_slack_user_count", "--slack_token=test-token", stdout=out)

        # Verify the project was resolved correctly (# stripped)
        project_with_hash.refresh_from_db()
        self.assertEqual(project_with_hash.slack_id, "C87654321")
        self.assertEqual(project_with_hash.slack, "https://owasp.slack.com/archives/C87654321")
        self.assertEqual(project_with_hash.slack_user_count, 3)

    @patch("website.management.commands.update_slack_user_count.requests.get")
    def test_channel_not_found_in_slack(self, mock_get):
        """Test handling when channel name doesn't exist in Slack"""
        # Delete the existing project_with_slack to test in isolation
        self.project_with_slack.delete()

        # Create a project with a channel name that doesn't exist
        project_missing = Project.objects.create(
            name="Project Missing Channel",
            slug="project-missing-channel",
            description="A project with non-existent channel",
            slack_channel="non-existent-channel",
        )

        # Mock responses: conversations.list returns empty
        mock_channels_response = Mock()
        mock_channels_response.json.return_value = {
            "ok": True,
            "channels": [
                {"name": "other-channel", "id": "C11111111"},
            ],
            "response_metadata": {"next_cursor": ""},
        }

        mock_get.return_value = mock_channels_response

        out = StringIO()
        call_command("update_slack_user_count", "--slack_token=test-token", stdout=out)

        # Verify the project was not updated
        project_missing.refresh_from_db()
        self.assertIsNone(project_missing.slack_id)
        self.assertEqual(project_missing.slack_user_count, 0)

        # Verify command output
        output = out.getvalue()
        self.assertIn("Could not find channel 'non-existent-channel'", output)

    @patch("website.management.commands.update_slack_user_count.requests.get")
    def test_channel_lookup_api_error(self, mock_get):
        """Test handling when channel lookup API fails"""
        # Remove slack_id from project to trigger channel lookup
        self.project_with_slack.slack_id = None
        self.project_with_slack.save()

        # Mock API error for conversations.list
        mock_error_response = Mock()
        mock_error_response.json.return_value = {
            "ok": False,
            "error": "invalid_auth",
        }
        mock_get.return_value = mock_error_response

        out = StringIO()
        call_command("update_slack_user_count", "--slack_token=test-token", stdout=out)

        # Verify the project was not updated
        self.project_with_slack.refresh_from_db()
        self.assertIsNone(self.project_with_slack.slack_id)
        self.assertEqual(self.project_with_slack.slack_user_count, 0)

        # Verify command output shows failure
        output = out.getvalue()
        self.assertIn("Failed to fetch channels list", output)

    @patch("website.management.commands.update_slack_user_count.requests.get")
    def test_channels_saved_to_database(self, mock_get):
        """Test that fetched Slack channels are saved to the SlackChannel table"""
        # Delete the existing project_with_slack to test in isolation
        self.project_with_slack.delete()

        # Create a project with only slack_channel (no slack_id or slack URL)
        project = Project.objects.create(
            name="Project For Channel Save Test",
            slug="project-channel-save-test",
            description="Test saving channels to database",
            slack_channel="project-save-test",
        )

        # Mock responses: conversations.list with channel data, then conversations.members
        mock_channels_response = Mock()
        mock_channels_response.json.return_value = {
            "ok": True,
            "channels": [
                {
                    "id": "C11111111",
                    "name": "project-save-test",
                    "topic": {"value": "Test topic", "creator": "U12345", "last_set": 1234567890},
                    "purpose": {"value": "Test purpose", "creator": "U12345", "last_set": 1234567890},
                    "num_members": 100,
                    "is_private": False,
                    "is_archived": False,
                    "is_general": False,
                    "creator": "U12345",
                    "created": 1234567890,
                },
                {
                    "id": "C22222222",
                    "name": "other-channel",
                    "topic": {"value": "Other topic", "creator": "U12345", "last_set": 1234567890},
                    "purpose": {"value": "Other purpose", "creator": "U12345", "last_set": 1234567890},
                    "num_members": 50,
                    "is_private": False,
                    "is_archived": False,
                    "is_general": False,
                    "creator": "U67890",
                    "created": 1234567890,
                },
            ],
            "response_metadata": {"next_cursor": ""},
        }
        mock_members_response = Mock()
        mock_members_response.json.return_value = {
            "ok": True,
            "members": ["U1", "U2", "U3", "U4", "U5"],  # 5 members
            "response_metadata": {"next_cursor": ""},
        }

        mock_get.side_effect = [mock_channels_response, mock_members_response]

        out = StringIO()
        call_command("update_slack_user_count", "--slack_token=test-token", stdout=out)

        # Verify channels were saved to the database
        self.assertEqual(SlackChannel.objects.count(), 2)

        # Verify first channel data
        channel1 = SlackChannel.objects.get(channel_id="C11111111")
        self.assertEqual(channel1.name, "project-save-test")
        self.assertEqual(channel1.topic, "Test topic")
        self.assertEqual(channel1.purpose, "Test purpose")
        self.assertEqual(channel1.creator, "U12345")
        self.assertEqual(channel1.slack_url, "https://owasp.slack.com/archives/C11111111")

        # Verify second channel data
        channel2 = SlackChannel.objects.get(channel_id="C22222222")
        self.assertEqual(channel2.name, "other-channel")

        # Verify the project was also updated
        project.refresh_from_db()
        self.assertEqual(project.slack_id, "C11111111")
        self.assertEqual(project.slack_user_count, 5)

        # Verify the SlackChannel is linked to the project
        channel1.refresh_from_db()
        self.assertIsNotNone(channel1.project)
        self.assertEqual(channel1.project.id, project.id)

        # Verify command output mentions saved channels
        output = out.getvalue()
        self.assertIn("Saved/updated 2 Slack channels", output)
