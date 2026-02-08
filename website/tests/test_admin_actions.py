import os
from unittest.mock import MagicMock, patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase

from website.admin import SlackBotActivityAdmin, backfill_slack_usernames
from website.models import Integration, Organization, SlackBotActivity, SlackIntegration


class BackfillSlackUsernamesTests(TestCase):
    """Tests for the backfill_slack_usernames admin action."""

    def setUp(self):
        """Set up test data."""
        self.site = AdminSite()
        self.admin = SlackBotActivityAdmin(SlackBotActivity, self.site)
        self.factory = RequestFactory()
        self.user = User.objects.create_superuser(username="admin", email="admin@test.com", password="password")

        # Create organization and integration
        self.organization = Organization.objects.create(name="Test Org", url="https://test.org")
        self.integration = Integration.objects.create(organization=self.organization)

    def test_backfill_updates_missing_usernames(self):
        """Test that backfill updates records with missing usernames."""
        # Create test activities
        activity1 = SlackBotActivity.objects.create(
            workspace_id="T04T40NHX",  # OWASP workspace
            workspace_name="OWASP",
            activity_type="team_join",
            user_id="U123456",
            username=None,  # Missing username
        )
        activity2 = SlackBotActivity.objects.create(
            workspace_id="T04T40NHX",
            workspace_name="OWASP",
            activity_type="command",
            user_id="U789012",
            username=None,  # Missing username
        )
        activity3 = SlackBotActivity.objects.create(
            workspace_id="T04T40NHX",
            workspace_name="OWASP",
            activity_type="message",
            user_id="U345678",
            username="Existing User",  # Already has username
        )

        # Mock the get_slack_username function - return username based on user_id
        def mock_username_lookup(client, user_id):
            username_map = {"U123456": "John Doe", "U789012": "Jane Smith"}
            return username_map.get(user_id)

        with patch("website.views.slack_handlers.get_slack_username") as mock_get_username:
            mock_get_username.side_effect = mock_username_lookup

            # Mock WebClient
            with patch("slack_sdk.web.WebClient") as mock_webclient:
                mock_client = MagicMock()
                mock_webclient.return_value = mock_client

                # Mock environment variable
                with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "test-token"}):
                    request = self.factory.get("/admin/")
                    request.user = self.user
                    request._messages = MagicMock()

                    queryset = SlackBotActivity.objects.all()
                    backfill_slack_usernames(self.admin, request, queryset)

        # Refresh from database
        activity1.refresh_from_db()
        activity2.refresh_from_db()
        activity3.refresh_from_db()

        # Check results
        self.assertEqual(activity1.username, "John Doe")
        self.assertEqual(activity2.username, "Jane Smith")
        self.assertEqual(activity3.username, "Existing User")  # Should not change

    def test_backfill_with_custom_workspace(self):
        """Test backfill with custom workspace integration."""
        # Create a custom workspace integration
        slack_integration = SlackIntegration.objects.create(
            integration=self.integration,
            workspace_name="T12345678",  # Custom workspace ID
            bot_access_token="xoxb-custom-token",
        )

        activity = SlackBotActivity.objects.create(
            workspace_id="T12345678",
            workspace_name="Custom Workspace",
            activity_type="team_join",
            user_id="U111222",
            username=None,
        )

        with patch("website.views.slack_handlers.get_slack_username") as mock_get_username:
            mock_get_username.return_value = "Custom User"

            with patch("slack_sdk.web.WebClient") as mock_webclient:
                mock_client = MagicMock()
                mock_webclient.return_value = mock_client

                request = self.factory.get("/admin/")
                request.user = self.user
                request._messages = MagicMock()

                queryset = SlackBotActivity.objects.filter(id=activity.id)
                backfill_slack_usernames(self.admin, request, queryset)

        activity.refresh_from_db()
        self.assertEqual(activity.username, "Custom User")

    def test_backfill_skips_records_without_user_id(self):
        """Test that backfill skips records without user_id."""
        activity = SlackBotActivity.objects.create(
            workspace_id="T04T40NHX",
            workspace_name="OWASP",
            activity_type="error",
            user_id=None,  # No user_id
            username=None,
        )

        with patch("website.views.slack_handlers.get_slack_username") as mock_get_username:
            with patch("slack_sdk.web.WebClient"):
                with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "test-token"}):
                    request = self.factory.get("/admin/")
                    request.user = self.user
                    request._messages = MagicMock()

                    queryset = SlackBotActivity.objects.filter(id=activity.id)
                    backfill_slack_usernames(self.admin, request, queryset)

        activity.refresh_from_db()
        self.assertIsNone(activity.username)
        # Should not call get_slack_username for records without user_id
        mock_get_username.assert_not_called()

    def test_backfill_handles_missing_integration(self):
        """Test that backfill handles missing integration gracefully."""
        activity = SlackBotActivity.objects.create(
            workspace_id="T99999999",  # Non-existent workspace
            workspace_name="Unknown Workspace",
            activity_type="command",
            user_id="U123456",
            username=None,
        )

        with patch("website.views.slack_handlers.get_slack_username") as mock_get_username:
            with patch("slack_sdk.web.WebClient"):
                request = self.factory.get("/admin/")
                request.user = self.user
                request._messages = MagicMock()

                queryset = SlackBotActivity.objects.filter(id=activity.id)
                backfill_slack_usernames(self.admin, request, queryset)

        activity.refresh_from_db()
        # Should remain None since workspace not found and not OWASP
        self.assertIsNone(activity.username)

    def test_backfill_handles_api_errors(self):
        """Test that backfill handles Slack API errors gracefully."""
        activity = SlackBotActivity.objects.create(
            workspace_id="T04T40NHX",
            workspace_name="OWASP",
            activity_type="team_join",
            user_id="U123456",
            username=None,
        )

        with patch("website.views.slack_handlers.get_slack_username") as mock_get_username:
            mock_get_username.side_effect = Exception("API Error")

            with patch("slack_sdk.web.WebClient"):
                with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "test-token"}):
                    request = self.factory.get("/admin/")
                    request.user = self.user
                    request._messages = MagicMock()

                    queryset = SlackBotActivity.objects.filter(id=activity.id)
                    backfill_slack_usernames(self.admin, request, queryset)

        activity.refresh_from_db()
        # Should remain None due to error
        self.assertIsNone(activity.username)
