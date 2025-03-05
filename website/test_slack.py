import json
import os
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from slack_sdk.errors import SlackApiError

from website.views.slackbot import slack_events, submit_bug  # Import the submit_bug and slack_events functions

# Set the DJANGO_SETTINGS_MODULE environment variable
os.environ["DJANGO_SETTINGS_MODULE"] = "blt.settings"


class SlackTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # No need to call settings.configure() here

    def setUp(self):
        # Create a test user for authentication
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpassword")
        # Log the user in
        self.client.login(username="testuser", password="testpassword")
        # Set up RequestFactory
        self.factory = RequestFactory()

    @patch("website.views.slackbot.client.chat_postMessage")
    def test_submit_bug_sends_message(self, mock_chat_post):
        """Test that submitting a bug sends a message to Slack."""
        mock_chat_post.return_value = {"ok": True, "ts": "1234567890.123456"}  # Mock successful response

        # Submit directly to the slackbot.submit_bug function using the view function directly
        from django.http import HttpRequest

        request = HttpRequest()
        request.method = "POST"
        request.POST = {"description": "Test bug description"}

        response = submit_bug(request)
        self.assertEqual(response.status_code, 200)

        # Verify the mock was called correctly
        mock_chat_post.assert_called_once_with(
            channel="#project-blt-bacon", text="A new bug has been reported: Test bug description"
        )

    @patch("website.views.slackbot.client.chat_postMessage")
    def test_team_join_with_custom_message(self, mock_chat_post):
        """Test that a team_join event sends a welcome message."""
        mock_chat_post.return_value = {"ok": True, "ts": "1234567890.123456"}  # Mock successful response

        # Create a request with team_join event
        request_data = {"event": {"type": "team_join", "user": {"id": "U01234567"}}}

        # Use RequestFactory to create a proper request
        json_data = json.dumps(request_data)
        request = self.factory.post("/slack/events/", data=json_data, content_type="application/json")

        # Call the slack_events view function
        response = slack_events(request)

        # Verify the welcome message was sent
        mock_chat_post.assert_called_once_with(
            channel="#project-blt-bacon", text="Welcome to the team, <@U01234567>! 🎉"
        )

        self.assertEqual(response.status_code, 200)

    @patch("website.views.slackbot.client.chat_postMessage")
    def test_submit_bug_handles_slack_error(self, mock_chat_post):
        """Test that submitting a bug handles Slack API errors."""
        mock_chat_post.side_effect = SlackApiError("Slack API error", response={"error": "error"})

        # Submit directly to the slackbot.submit_bug function using the view function directly
        from django.http import HttpRequest

        request = HttpRequest()
        request.method = "POST"
        request.POST = {"description": "Test bug description"}

        response = submit_bug(request)

        # Even with Slack error, the HTTP response should be successful
        self.assertEqual(response.status_code, 200)
        # Verify the mock was called
        mock_chat_post.assert_called_once()
