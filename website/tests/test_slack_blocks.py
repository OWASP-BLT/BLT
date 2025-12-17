from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from website.models import SlackHuddle, SlackHuddleParticipant, SlackPoll, SlackPollOption, SlackPollVote
from website.views.slack_handlers import build_huddle_blocks, build_poll_blocks


class SlackBlocksTests(TestCase):
    def test_build_poll_blocks_contains_options_and_counts_and_bar(self):
        poll = SlackPoll.objects.create(
            workspace_id="T070JPE5BQQ", channel_id="C123", creator_id="U123", question="Best time?", status="active"
        )
        opt_a = SlackPollOption.objects.create(poll=poll, option_text="Morning", option_number=0)
        opt_b = SlackPollOption.objects.create(poll=poll, option_text="Evening", option_number=1)
        SlackPollVote.objects.create(poll=poll, option=opt_a, voter_id="U1")

        blocks = build_poll_blocks(poll)
        block_text = str(blocks)
        self.assertIn("Best time?", block_text)
        self.assertIn("Morning", block_text)
        self.assertIn("Evening", block_text)
        # ensure non-zero bar shows at least one block character
        self.assertIn("█", block_text)

    def test_build_huddle_blocks_contains_title_and_actions(self):
        h = SlackHuddle.objects.create(
            workspace_id="T070JPE5BQQ",
            channel_id="C123",
            creator_id="U123",
            title="Standup",
            description="Daily",
            status="scheduled",
            scheduled_at=timezone.now() + timedelta(hours=2),
        )
        SlackHuddleParticipant.objects.create(huddle=h, user_id="U1", response="accepted")

        blocks = build_huddle_blocks(h)
        block_text = str(blocks)
        self.assertIn("Standup", block_text)
        # ensure action buttons are present
        self.assertTrue(any(b.get("type") == "actions" for b in blocks))
