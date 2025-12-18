from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from website.models import SlackHuddle, SlackHuddleParticipant, SlackPoll, SlackPollOption, SlackPollVote, SlackReminder
from website.views.slack_handlers import (
    handle_huddle_cancel,
    handle_huddle_command,
    handle_huddle_response,
    handle_poll_close,
    handle_poll_vote,
    handle_reminder_cancel,
)


class SlackInteractionHandlerTests(TestCase):
    def setUp(self):
        self.workspace_id = "TTEST"
        self.channel_id = "C123"
        self.creator_id = "UCREATOR"
        self.other_id = "UOTHER"

    @patch("website.views.slack_handlers.WebClient")
    def test_handle_poll_vote_success_and_duplicate(self, mock_webclient):
        # Create poll and options
        poll = SlackPoll.objects.create(
            workspace_id=self.workspace_id,
            channel_id=self.channel_id,
            creator_id=self.creator_id,
            question="Best time?",
            status="active",
        )
        opt_a = SlackPollOption.objects.create(poll=poll, option_text="Morning", option_number=0)

        workspace_client = mock_webclient.return_value
        workspace_client.chat_update.return_value = {"ok": True}

        payload = {
            "user": {"id": self.other_id},
            "actions": [{"action_id": f"poll_vote_{opt_a.id}"}],
        }
        # First vote succeeds
        response = handle_poll_vote(payload, workspace_client)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(SlackPollVote.objects.filter(poll=poll).count(), 1)
        workspace_client.chat_update.assert_called()

        # Duplicate vote yields informative message
        response2 = handle_poll_vote(payload, workspace_client)
        self.assertEqual(response2.status_code, 200)
        self.assertIn("already", response2.content.decode().lower())
        self.assertEqual(SlackPollVote.objects.filter(poll=poll).count(), 1)

    @patch("website.views.slack_handlers.WebClient")
    def test_handle_poll_vote_closed_poll(self, mock_webclient):
        poll = SlackPoll.objects.create(
            workspace_id=self.workspace_id,
            channel_id=self.channel_id,
            creator_id=self.creator_id,
            question="Best time?",
            status="closed",
        )
        opt = SlackPollOption.objects.create(poll=poll, option_text="Morning", option_number=0)
        workspace_client = mock_webclient.return_value
        payload = {"user": {"id": self.other_id}, "actions": [{"action_id": f"poll_vote_{opt.id}"}]}
        response = handle_poll_vote(payload, workspace_client)
        self.assertEqual(response.status_code, 200)
        self.assertIn("closed", response.content.decode().lower())

    @patch("website.views.slack_handlers.WebClient")
    def test_handle_poll_close_permissions_and_success(self, mock_webclient):
        poll = SlackPoll.objects.create(
            workspace_id=self.workspace_id,
            channel_id=self.channel_id,
            creator_id=self.creator_id,
            question="Best time?",
            status="active",
        )
        workspace_client = mock_webclient.return_value
        workspace_client.chat_update.return_value = {"ok": True}

        # Non-creator cannot close
        payload = {"actions": [{"action_id": f"poll_close_{poll.id}"}]}
        resp = handle_poll_close(payload, workspace_client, self.other_id)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("only", resp.content.decode().lower())

        # Creator closes successfully
        resp2 = handle_poll_close(payload, workspace_client, self.creator_id)
        self.assertEqual(resp2.status_code, 200)
        poll.refresh_from_db()
        self.assertEqual(poll.status, "closed")
        workspace_client.chat_update.assert_called()

    def test_handle_reminder_cancel_permissions_and_success(self):
        r = SlackReminder.objects.create(
            workspace_id=self.workspace_id,
            creator_id=self.creator_id,
            target_type="user",
            target_id=self.other_id,
            message="Ping",
            status="pending",
            remind_at=timezone.now() + timezone.timedelta(minutes=1),
        )
        # Non-creator cannot cancel
        payload = {"actions": [{"action_id": f"reminder_cancel_{r.id}"}]}
        resp = handle_reminder_cancel(payload, self.other_id)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("only", resp.content.decode().lower())

        # Creator cancels
        resp2 = handle_reminder_cancel(payload, self.creator_id)
        self.assertEqual(resp2.status_code, 200)
        r.refresh_from_db()
        self.assertEqual(r.status, "cancelled")

    @patch("website.views.slack_handlers.WebClient")
    def test_handle_huddle_response_accept_decline(self, mock_webclient):
        h = SlackHuddle.objects.create(
            workspace_id=self.workspace_id,
            channel_id=self.channel_id,
            creator_id=self.creator_id,
            title="Standup",
            description="Daily",
            status="scheduled",
            scheduled_at=timezone.now() + timezone.timedelta(hours=1),
        )
        workspace_client = mock_webclient.return_value
        workspace_client.chat_update.return_value = {"ok": True}

        # Accept
        payload_accept = {"actions": [{"action_id": f"huddle_accept_{h.id}"}]}
        resp_a = handle_huddle_response(payload_accept, workspace_client, self.other_id, "accepted")
        self.assertEqual(resp_a.status_code, 200)
        p = SlackHuddleParticipant.objects.get(huddle=h, user_id=self.other_id)
        self.assertEqual(p.response, "accepted")

        # Decline
        payload_decline = {"actions": [{"action_id": f"huddle_decline_{h.id}"}]}
        resp_d = handle_huddle_response(payload_decline, workspace_client, self.other_id, "declined")
        self.assertEqual(resp_d.status_code, 200)
        p.refresh_from_db()
        self.assertEqual(p.response, "declined")

    @patch("website.views.slack_handlers.WebClient")
    def test_handle_huddle_cancel_permissions_and_already_started(self, mock_webclient):
        h = SlackHuddle.objects.create(
            workspace_id=self.workspace_id,
            channel_id=self.channel_id,
            creator_id=self.creator_id,
            title="Standup",
            description="Daily",
            status="scheduled",
            scheduled_at=timezone.now() + timezone.timedelta(hours=1),
        )
        workspace_client = mock_webclient.return_value
        workspace_client.chat_update.return_value = {"ok": True}

        payload = {"actions": [{"action_id": f"huddle_cancel_{h.id}"}]}
        # Non-creator cannot cancel
        resp = handle_huddle_cancel(payload, workspace_client, self.other_id)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("only", resp.content.decode().lower())

        # Set started and try cancel by creator
        h.status = "started"
        h.save()
        resp2 = handle_huddle_cancel(payload, workspace_client, self.creator_id)
        self.assertEqual(resp2.status_code, 200)
        self.assertIn("no longer", resp2.content.decode().lower())

    @patch("website.views.slack_handlers.WebClient")
    def test_huddle_invalid_user_mentions(self, mock_webclient):
        workspace_client = mock_webclient.return_value

        # First call returns valid for U2, second invalid for U999
        def users_info_side_effect(user):
            if user == "U999":
                return {"ok": False}
            return {"ok": True, "user": {"id": user}}

        workspace_client.users_info.side_effect = users_info_side_effect

        text = '"Standup" "Daily" in 10 minutes with <@U2> <@U999>'
        activity = MagicMock()
        # Clear entire cache to avoid rate-limit interference
        cache.clear()

        resp = handle_huddle_command(
            workspace_client, self.creator_id, self.workspace_id, self.channel_id, text, activity
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("not found", resp.content.decode().lower())

    @patch("website.views.slack_handlers.timezone")
    @patch("website.views.slack_handlers.WebClient")
    def test_huddle_at_time_in_past_error(self, mock_webclient, mock_tz):
        now = timezone.now()
        fixed = now.replace(hour=14, minute=0, second=0, microsecond=0)
        mock_tz.now.return_value = fixed

        workspace_client = mock_webclient.return_value
        activity = MagicMock()
        text = '"Standup" "Daily" at 1:00 PM'
        resp = handle_huddle_command(
            workspace_client, self.creator_id, self.workspace_id, self.channel_id, text, activity
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("already passed", resp.content.decode().lower())

    def test_handle_reminder_cancel_already_cancelled(self):
        """Test attempting to cancel an already-cancelled reminder."""
        r = SlackReminder.objects.create(
            workspace_id=self.workspace_id,
            creator_id=self.creator_id,
            target_type="user",
            target_id=self.other_id,
            message="Ping",
            status="cancelled",
            remind_at=timezone.now() + timezone.timedelta(minutes=1),
        )
        payload = {"actions": [{"action_id": f"reminder_cancel_{r.id}"}]}
        resp = handle_reminder_cancel(payload, self.creator_id)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("no longer pending", resp.content.decode().lower())

    def test_handle_reminder_cancel_already_sent(self):
        """Test attempting to cancel an already-sent reminder."""
        r = SlackReminder.objects.create(
            workspace_id=self.workspace_id,
            creator_id=self.creator_id,
            target_type="user",
            target_id=self.other_id,
            message="Ping",
            status="sent",
            remind_at=timezone.now() - timezone.timedelta(minutes=1),
        )
        payload = {"actions": [{"action_id": f"reminder_cancel_{r.id}"}]}
        resp = handle_reminder_cancel(payload, self.creator_id)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("no longer pending", resp.content.decode().lower())

    def test_handle_reminder_cancel_invalid_id(self):
        """Test attempting to cancel with an invalid reminder ID (404 case)."""
        payload = {"actions": [{"action_id": "reminder_cancel_99999"}]}
        resp = handle_reminder_cancel(payload, self.creator_id)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("not found", resp.content.decode().lower())

    @patch("website.views.slack_handlers.WebClient")
    def test_handle_poll_close_already_closed(self, mock_webclient):
        """Test attempting to close an already-closed poll."""
        poll = SlackPoll.objects.create(
            workspace_id=self.workspace_id,
            channel_id=self.channel_id,
            creator_id=self.creator_id,
            question="Best time?",
            status="closed",
        )
        workspace_client = mock_webclient.return_value
        payload = {"actions": [{"action_id": f"poll_close_{poll.id}"}]}
        resp = handle_poll_close(payload, workspace_client, self.creator_id)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("already closed", resp.content.decode().lower())

    @patch("website.views.slack_handlers.WebClient")
    def test_handle_poll_close_invalid_id(self, mock_webclient):
        """Test attempting to close with an invalid poll ID (404 case)."""
        workspace_client = mock_webclient.return_value
        payload = {"actions": [{"action_id": "poll_close_99999"}]}
        resp = handle_poll_close(payload, workspace_client, self.creator_id)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("not found", resp.content.decode().lower())

    @patch("website.views.slack_handlers.WebClient")
    def test_handle_poll_vote_slack_api_failure(self, mock_webclient):
        """Test handling Slack API failures during chat_update."""
        poll = SlackPoll.objects.create(
            workspace_id=self.workspace_id,
            channel_id=self.channel_id,
            creator_id=self.creator_id,
            question="Best time?",
            status="active",
        )
        opt = SlackPollOption.objects.create(poll=poll, option_text="Morning", option_number=0)

        workspace_client = mock_webclient.return_value
        # Simulate Slack API error
        from slack_sdk.errors import SlackApiError

        workspace_client.chat_update.side_effect = SlackApiError(
            message="channel_not_found", response={"error": "channel_not_found"}
        )

        payload = {"user": {"id": self.other_id}, "actions": [{"action_id": f"poll_vote_{opt.id}"}]}
        response = handle_poll_vote(payload, workspace_client)
        self.assertEqual(response.status_code, 200)
        # Vote should still be recorded despite API failure
        self.assertEqual(SlackPollVote.objects.filter(poll=poll).count(), 1)
