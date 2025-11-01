from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from website.models import Organization, ReminderSettings, UserProfile


class SlackConnectionTests(TestCase):
    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(username="testuser", password="testpass123", email="test@test.com")
        self.client = Client()
        self.client.login(username="testuser", password="testpass123")

        # Create organization with check-ins enabled
        self.organization = Organization.objects.create(
            name="Test Organization", url="https://test.org", check_ins_enabled=True
        )

        # Ensure user profile exists
        self.profile = self.user.userprofile
        self.profile.team = self.organization
        self.profile.save()

    def test_connect_slack_account_redirects_to_oauth(self):
        """Test that connect_slack_account redirects to Slack OAuth URL"""
        with patch("website.views.daily_reminders.SLACK_CLIENT_ID", "test_client_id"):
            response = self.client.get(reverse("connect_slack_account"))
            self.assertEqual(response.status_code, 302)
            self.assertIn("slack.com/oauth/v2/authorize", response.url)

    def test_connect_slack_account_without_client_id(self):
        """Test error handling when Slack client ID is not configured"""
        with patch("website.views.daily_reminders.SLACK_CLIENT_ID", None):
            response = self.client.get(reverse("connect_slack_account"))
            self.assertEqual(response.status_code, 302)
            self.assertRedirects(response, reverse("reminder_settings"))

    @patch("website.views.daily_reminders.requests.post")
    def test_slack_oauth_callback_success(self, mock_post):
        """Test successful Slack OAuth callback"""
        # Mock successful OAuth response
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True, "authed_user": {"id": "U123456"}}
        mock_post.return_value = mock_response

        with patch("website.views.daily_reminders.SLACK_CLIENT_ID", "test_client_id"):
            with patch("website.views.daily_reminders.SLACK_CLIENT_SECRET", "test_secret"):
                response = self.client.get(
                    reverse("slack_oauth_callback"), {"code": "test_code", "state": "testuser"}
                )

                self.assertEqual(response.status_code, 302)
                self.assertRedirects(response, reverse("reminder_settings"))

                # Check that Slack user ID was saved
                self.profile.refresh_from_db()
                self.assertEqual(self.profile.slack_user_id, "U123456")

    def test_slack_oauth_callback_invalid_state(self):
        """Test OAuth callback with invalid state parameter"""
        response = self.client.get(reverse("slack_oauth_callback"), {"code": "test_code", "state": "wronguser"})

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("reminder_settings"))

        # Check that Slack user ID was not saved
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.slack_user_id)

    def test_disconnect_slack_account(self):
        """Test disconnecting Slack account"""
        # Set up connected account
        self.profile.slack_user_id = "U123456"
        self.profile.save()

        # Create reminder settings with Slack enabled
        reminder_settings = ReminderSettings.objects.create(
            user=self.user, is_active=True, slack_notifications_enabled=True
        )

        # Disconnect
        response = self.client.post(reverse("disconnect_slack_account"))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("reminder_settings"))

        # Check that Slack user ID was removed
        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.slack_user_id)

        # Check that Slack notifications were disabled
        reminder_settings.refresh_from_db()
        self.assertFalse(reminder_settings.slack_notifications_enabled)

    @patch("website.views.daily_reminders.WebClient")
    def test_send_test_slack_reminder_success(self, mock_webclient):
        """Test sending test Slack reminder"""
        # Set up connected account
        self.profile.slack_user_id = "U123456"
        self.profile.save()

        # Mock Slack client
        mock_client = MagicMock()
        mock_client.chat_postMessage.return_value = {"ok": True}
        mock_webclient.return_value = mock_client

        with patch("website.views.daily_reminders.SLACK_BOT_TOKEN", "test_token"):
            response = self.client.post(reverse("send_test_slack_reminder"))

            self.assertEqual(response.status_code, 302)
            self.assertRedirects(response, reverse("reminder_settings"))

            # Verify Slack API was called
            mock_client.chat_postMessage.assert_called_once()

    def test_send_test_slack_reminder_without_connection(self):
        """Test sending test Slack reminder without connected account"""
        response = self.client.post(reverse("send_test_slack_reminder"))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse("reminder_settings"))

    def test_reminder_settings_form_includes_slack_field(self):
        """Test that reminder settings form includes Slack notifications field"""
        response = self.client.get(reverse("reminder_settings"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "slack_notifications_enabled")

    def test_reminder_settings_shows_slack_connection_status(self):
        """Test that reminder settings page shows Slack connection status"""
        response = self.client.get(reverse("reminder_settings"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Connect Slack Account")

        # Connect Slack account
        self.profile.slack_user_id = "U123456"
        self.profile.save()

        response = self.client.get(reverse("reminder_settings"))
        self.assertContains(response, "Slack account connected")


class DailyCheckinReminderCommandTests(TestCase):
    def setUp(self):
        # Create test user with organization
        self.user = User.objects.create_user(username="testuser", password="testpass123", email="test@test.com")

        # Create organization with check-ins enabled
        self.organization = Organization.objects.create(
            name="Test Organization", url="https://test.org", check_ins_enabled=True
        )

        # Set user profile team
        self.profile = self.user.userprofile
        self.profile.team = self.organization
        self.profile.slack_user_id = "U123456"
        self.profile.save()

    @patch("website.management.commands.daily_checkin_reminder.WebClient")
    def test_command_sends_slack_reminders(self, mock_webclient):
        """Test that the command sends Slack DM reminders when enabled"""
        from django.core.management import call_command

        # Create reminder settings with Slack enabled
        ReminderSettings.objects.create(user=self.user, is_active=True, slack_notifications_enabled=True)

        # Mock Slack client
        mock_client = MagicMock()
        mock_client.chat_postMessage.return_value = {"ok": True}
        mock_webclient.return_value = mock_client

        with patch("website.management.commands.daily_checkin_reminder.SLACK_BOT_TOKEN", "test_token"):
            call_command("daily_checkin_reminder")

            # Verify Slack API was called
            mock_client.chat_postMessage.assert_called_once()

    @patch("website.management.commands.daily_checkin_reminder.WebClient")
    def test_command_skips_slack_when_not_enabled(self, mock_webclient):
        """Test that the command skips Slack DM when not enabled"""
        from django.core.management import call_command

        # Create reminder settings with Slack disabled
        ReminderSettings.objects.create(user=self.user, is_active=True, slack_notifications_enabled=False)

        # Mock Slack client
        mock_client = MagicMock()
        mock_webclient.return_value = mock_client

        with patch("website.management.commands.daily_checkin_reminder.SLACK_BOT_TOKEN", "test_token"):
            call_command("daily_checkin_reminder")

            # Verify Slack API was not called
            mock_client.chat_postMessage.assert_not_called()
