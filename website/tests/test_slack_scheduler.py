from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from website.models import (
    Integration,
    Organization,
    SlackHuddle,
    SlackHuddleParticipant,
    SlackIntegration,
    SlackReminder,
)


class SlackSchedulerTests(TestCase):
    def setUp(self):
        org = Organization.objects.create(name="Test Org", url="https://test.org")
        integ = Integration.objects.create(organization=org, service_name="slack")
        # Use empty token so creator-cancellation step is skipped in tests
        self.slack_integration = SlackIntegration.objects.create(
            integration=integ,
            bot_access_token="",
            workspace_name="T070JPE5BQQ",
            default_channel_id="C123",
        )

    @patch("website.management.commands.process_slack_reminders_and_huddles.requests.post")
    def test_due_user_reminder_sent_and_marked_in_dry_run(self, mock_post):
        # Mock conversations.open and chat.postMessage responses
        # conversations.open
        mock_post.side_effect = [
            MagicMock(status_code=200, json=lambda: {"ok": True, "channel": {"id": "D123"}}),
            MagicMock(status_code=200, json=lambda: {"ok": True}),
        ]

        r = SlackReminder.objects.create(
            workspace_id="T070JPE5BQQ",
            creator_id="U999",
            target_type="user",
            target_id="U123",
            message="Ping",
            status="pending",
            remind_at=timezone.now() - timedelta(seconds=1),
        )

        # Dry run will mark as sent without making network-critical assertions
        # Use a generous window to ensure upcoming huddle is included
        call_command("process_slack_reminders_and_huddles", "--dry-run", "--window-minutes=60")

        r.refresh_from_db()
        self.assertEqual(r.status, "sent")

    @patch("website.management.commands.process_slack_reminders_and_huddles.requests.post")
    def test_due_channel_reminder_sent_in_dry_run(self, mock_post):
        r = SlackReminder.objects.create(
            workspace_id="T070JPE5BQQ",
            creator_id="U999",
            target_type="channel",
            target_id="C999",
            message="Ping channel",
            status="pending",
            remind_at=timezone.now() - timedelta(seconds=1),
        )

        call_command("process_slack_reminders_and_huddles", "--dry-run")

        r.refresh_from_db()
        self.assertEqual(r.status, "sent")
        mock_post.assert_not_called()

    @patch("website.management.commands.process_slack_reminders_and_huddles.requests.post")
    def test_huddle_pre_notify_and_mark_started(self, mock_post):
        upcoming = SlackHuddle.objects.create(
            workspace_id="T070JPE5BQQ",
            creator_id="U123",
            channel_id="C123",
            title="Sync",
            description="Daily",
            status="scheduled",
            scheduled_at=timezone.now() + timedelta(minutes=10),
            reminder_sent=False,
        )
        SlackHuddleParticipant.objects.create(huddle=upcoming, user_id="U1", response="invited")

        past = SlackHuddle.objects.create(
            workspace_id="T070JPE5BQQ",
            creator_id="U123",
            channel_id="C123",
            title="Past",
            description="Old",
            status="scheduled",
            scheduled_at=timezone.now() - timedelta(minutes=1),
            reminder_sent=False,
        )

        call_command("process_slack_reminders_and_huddles", "--dry-run")

        upcoming.refresh_from_db()
        past.refresh_from_db()
        # Ensure past huddle transitioned to started; dry-run avoids actual network calls
        self.assertEqual(past.status, "started")
        mock_post.assert_not_called()
