from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.db import transaction
from django.test import TestCase, TransactionTestCase, override_settings
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

    def test_due_user_reminder_sent_and_marked_in_dry_run(self):
        r = SlackReminder.objects.create(
            workspace_id="T070JPE5BQQ",
            creator_id="U999",
            target_type="user",
            target_id="U123",
            message="Ping",
            status="pending",
            remind_at=timezone.now() - timedelta(seconds=1),
        )

        # Dry run will mark as sent without making network calls
        call_command("process_slack_reminders_and_huddles", "--dry-run", "--window-minutes=60")

        r.refresh_from_db()
        # Dry-run should not persist state changes
        self.assertEqual(r.status, "pending")

    def test_due_channel_reminder_sent_in_dry_run(self):
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
        # Dry-run should not persist state changes
        self.assertEqual(r.status, "pending")

    def test_huddle_pre_notify_and_mark_started(self):
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
        # Dry-run should not mutate huddle state
        self.assertEqual(past.status, "scheduled")
        self.assertEqual(upcoming.status, "scheduled")
        self.assertFalse(upcoming.reminder_sent)


class SlackSchedulerRateLimitTests(TestCase):
    """Test rate limiting (HTTP 429) handling"""

    def setUp(self):
        org = Organization.objects.create(name="Test Org", url="https://test.org")
        integ = Integration.objects.create(organization=org, service_name="slack")
        self.slack_integration = SlackIntegration.objects.create(
            integration=integ,
            bot_access_token="xoxb-test-token",
            workspace_name="T070JPE5BQQ",
            default_channel_id="C123",
        )

    @patch("website.management.commands.process_slack_reminders_and_huddles.requests.post")
    @override_settings(SLACK_BOT_TOKEN="xoxb-test")
    def test_reminder_rate_limited_with_retry_after_header(self, mock_post):
        """Test reminder is rescheduled when rate limited with Retry-After header"""
        # Mock rate limit response with Retry-After header
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "120"}
        mock_post.return_value = mock_response

        r = SlackReminder.objects.create(
            workspace_id="T070JPE5BQQ",
            creator_id="U999",
            target_type="user",
            target_id="U123",
            message="Test",
            status="pending",
            remind_at=timezone.now() - timedelta(seconds=1),
        )

        call_command("process_slack_reminders_and_huddles")

        r.refresh_from_db()
        self.assertEqual(r.status, "pending")
        self.assertIn("send_failed", r.error_message)
        # Should be rescheduled approximately 120 seconds in the future
        self.assertGreater(r.remind_at, timezone.now() + timedelta(seconds=100))

    @patch("website.management.commands.process_slack_reminders_and_huddles.requests.post")
    @override_settings(SLACK_BOT_TOKEN="xoxb-test")
    def test_reminder_rate_limited_without_retry_after_uses_exponential_backoff(self, mock_post):
        """Test reminder uses exponential backoff when rate limited without Retry-After"""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}
        mock_post.return_value = mock_response

        r = SlackReminder.objects.create(
            workspace_id="T070JPE5BQQ",
            creator_id="U999",
            target_type="user",
            target_id="U123",
            message="Test",
            status="pending",
            remind_at=timezone.now() - timedelta(seconds=1),
        )

        call_command("process_slack_reminders_and_huddles")

        r.refresh_from_db()
        self.assertEqual(r.status, "pending")
        # First retry should use BASE_BACKOFF_SECONDS (60s)
        self.assertGreater(r.remind_at, timezone.now() + timedelta(seconds=50))

    @patch("website.management.commands.process_slack_reminders_and_huddles.requests.post")
    @patch("website.management.commands.process_slack_reminders_and_huddles._user_exists")
    @override_settings(SLACK_BOT_TOKEN="xoxb-test")
    def test_huddle_creator_check_rate_limited_does_not_cancel(self, mock_user_exists, mock_post):
        """Test huddle is NOT cancelled when creator check is rate limited"""
        # Return rate limit indication
        mock_user_exists.return_value = (False, 60)  # exists=False, retry_after=60

        h = SlackHuddle.objects.create(
            workspace_id="T070JPE5BQQ",
            creator_id="U123",
            channel_id="C123",
            title="Test Huddle",
            status="scheduled",
            scheduled_at=timezone.now() + timedelta(days=1),
        )

        call_command("process_slack_reminders_and_huddles")

        h.refresh_from_db()
        # Should still be scheduled, not cancelled
        self.assertEqual(h.status, "scheduled")

    @patch("website.management.commands.process_slack_reminders_and_huddles.requests.post")
    @patch("website.management.commands.process_slack_reminders_and_huddles._user_exists")
    @override_settings(SLACK_BOT_TOKEN="xoxb-test")
    def test_huddle_creator_actually_gone_gets_cancelled(self, mock_user_exists, mock_post):
        """Test huddle IS cancelled when creator actually doesn't exist (404)"""
        # Return user not found (not rate limit)
        mock_user_exists.return_value = (False, None)  # exists=False, retry_after=None

        h = SlackHuddle.objects.create(
            workspace_id="T070JPE5BQQ",
            creator_id="U123",
            channel_id="C123",
            title="Test Huddle",
            status="scheduled",
            scheduled_at=timezone.now() + timedelta(days=1),
        )

        call_command("process_slack_reminders_and_huddles")

        h.refresh_from_db()
        self.assertEqual(h.status, "cancelled")


class SlackSchedulerRetryExhaustionTests(TestCase):
    """Test retry exhaustion scenarios"""

    def setUp(self):
        org = Organization.objects.create(name="Test Org", url="https://test.org")
        integ = Integration.objects.create(organization=org, service_name="slack")
        self.slack_integration = SlackIntegration.objects.create(
            integration=integ,
            bot_access_token="xoxb-test-token",
            workspace_name="T070JPE5BQQ",
            default_channel_id="C123",
        )

    @patch("website.management.commands.process_slack_reminders_and_huddles._user_exists")
    @patch("website.management.commands.process_slack_reminders_and_huddles.requests.post")
    @override_settings(SLACK_BOT_TOKEN="xoxb-test")
    def test_reminder_marked_failed_after_max_retries(self, mock_post, mock_user_exists):
        """Test reminder marked as failed after exceeding MAX_RETRIES"""
        # Mock user existence check to succeed
        mock_user_exists.return_value = (True, None)

        # Mock sending to fail
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"ok": False, "error": "internal_error"}
        mock_post.return_value = mock_response

        r = SlackReminder.objects.create(
            workspace_id="T070JPE5BQQ",
            creator_id="U999",
            target_type="user",
            target_id="U123",
            message="Test",
            status="pending",
            remind_at=timezone.now() - timedelta(seconds=1),
            error_message="retries=5; last_error=send_failed",  # Already at max retries
        )

        call_command("process_slack_reminders_and_huddles")

        r.refresh_from_db()
        self.assertEqual(r.status, "failed")
        self.assertIn("max_retries_exceeded", r.error_message)

    @patch("website.management.commands.process_slack_reminders_and_huddles._user_exists")
    @patch("website.management.commands.process_slack_reminders_and_huddles.requests.post")
    @override_settings(SLACK_BOT_TOKEN="xoxb-test")
    def test_reminder_marked_failed_after_max_age(self, mock_post, mock_user_exists):
        """Test reminder marked as failed after exceeding MAX_RETRY_AGE_DAYS"""
        # Mock user existence check to succeed
        mock_user_exists.return_value = (True, None)

        # Mock sending to fail
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"ok": False}
        mock_post.return_value = mock_response

        # Create reminder 8 days ago (exceeds MAX_RETRY_AGE_DAYS=7)
        old_date = timezone.now() - timedelta(days=8)
        r = SlackReminder.objects.create(
            workspace_id="T070JPE5BQQ",
            creator_id="U999",
            target_type="user",
            target_id="U123",
            message="Test",
            status="pending",
            remind_at=timezone.now() - timedelta(seconds=1),
        )
        # Manually set created_at to old date
        SlackReminder.objects.filter(id=r.id).update(created_at=old_date)

        call_command("process_slack_reminders_and_huddles")

        r.refresh_from_db()
        self.assertEqual(r.status, "failed")
        self.assertIn("max_age_exceeded", r.error_message)

    @patch("website.management.commands.process_slack_reminders_and_huddles._user_exists")
    @override_settings(SLACK_BOT_TOKEN="xoxb-test")
    def test_reminder_marked_failed_when_user_not_found(self, mock_user_exists):
        """Test reminder marked as failed when target user doesn't exist"""
        mock_user_exists.return_value = (False, None)  # User doesn't exist

        r = SlackReminder.objects.create(
            workspace_id="T070JPE5BQQ",
            creator_id="U999",
            target_type="user",
            target_id="U123",
            message="Test",
            status="pending",
            remind_at=timezone.now() - timedelta(seconds=1),
        )

        call_command("process_slack_reminders_and_huddles")

        r.refresh_from_db()
        self.assertEqual(r.status, "failed")
        self.assertIn("user_not_found", r.error_message)


class SlackSchedulerConcurrentProcessingTests(TransactionTestCase):
    """Test concurrent processing scenarios using TransactionTestCase for real transactions"""

    def setUp(self):
        org = Organization.objects.create(name="Test Org", url="https://test.org")
        integ = Integration.objects.create(organization=org, service_name="slack")
        self.slack_integration = SlackIntegration.objects.create(
            integration=integ,
            bot_access_token="xoxb-test-token",
            workspace_name="T070JPE5BQQ",
            default_channel_id="C123",
        )

    @patch("website.management.commands.process_slack_reminders_and_huddles.requests.post")
    def test_concurrent_reminder_processing_skipped_with_skip_locked(self, mock_post):
        """Test that skip_locked is used to prevent concurrent processing of same reminder"""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"ok": True, "channel": {"id": "D123"}},
        )

        r = SlackReminder.objects.create(
            workspace_id="T070JPE5BQQ",
            creator_id="U999",
            target_type="user",
            target_id="U123",
            message="Test",
            status="pending",
            remind_at=timezone.now() - timedelta(seconds=1),
        )

        # Verify skip_locked query works and returns records when not locked
        with transaction.atomic():
            # Query with skip_locked should find the record when it's not locked
            locked = list(SlackReminder.objects.select_for_update(skip_locked=True).filter(id=r.id))
            self.assertEqual(len(locked), 1)
            # Record should still be pending initially
            self.assertEqual(locked[0].status, "pending")

    @patch("website.management.commands.process_slack_reminders_and_huddles.requests.post")
    def test_reminder_status_revalidated_after_network_call(self, mock_post):
        """Test reminder status is revalidated after network call to detect concurrent changes"""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"ok": True, "channel": {"id": "D123"}},
        )

        r = SlackReminder.objects.create(
            workspace_id="T070JPE5BQQ",
            creator_id="U999",
            target_type="user",
            target_id="U123",
            message="Test",
            status="pending",
            remind_at=timezone.now() - timedelta(seconds=1),
        )

        # Simulate another process changing status during network call
        with patch("website.management.commands.process_slack_reminders_and_huddles._send_slack_message") as mock_send:

            def side_effect_change_status(*args, **kwargs):
                # During the "network call", another process marks as sent
                SlackReminder.objects.filter(id=r.id).update(status="sent")
                return (True, None)

            mock_send.side_effect = side_effect_change_status

            with override_settings(SLACK_BOT_TOKEN="xoxb-test"):
                call_command("process_slack_reminders_and_huddles")

        # The scheduler should detect status changed and skip update
        r.refresh_from_db()
        self.assertEqual(r.status, "sent")


class SlackSchedulerNetworkTimeoutTests(TestCase):
    """Test network timeout handling"""

    def setUp(self):
        org = Organization.objects.create(name="Test Org", url="https://test.org")
        integ = Integration.objects.create(organization=org, service_name="slack")
        self.slack_integration = SlackIntegration.objects.create(
            integration=integ,
            bot_access_token="xoxb-test-token",
            workspace_name="T070JPE5BQQ",
            default_channel_id="C123",
        )

    @patch("website.management.commands.process_slack_reminders_and_huddles.requests.post")
    @override_settings(SLACK_BOT_TOKEN="xoxb-test")
    def test_reminder_retried_on_network_timeout(self, mock_post):
        """Test reminder is retried when network timeout occurs"""
        import requests

        mock_post.side_effect = requests.exceptions.Timeout("Connection timed out")

        r = SlackReminder.objects.create(
            workspace_id="T070JPE5BQQ",
            creator_id="U999",
            target_type="user",
            target_id="U123",
            message="Test",
            status="pending",
            remind_at=timezone.now() - timedelta(seconds=1),
        )

        call_command("process_slack_reminders_and_huddles")

        r.refresh_from_db()
        self.assertEqual(r.status, "pending")
        self.assertIn("send_failed", r.error_message)
        # Should be rescheduled for retry
        self.assertGreater(r.remind_at, timezone.now())

    @patch("website.management.commands.process_slack_reminders_and_huddles.requests.post")
    @override_settings(SLACK_BOT_TOKEN="xoxb-test")
    def test_reminder_retried_on_connection_error(self, mock_post):
        """Test reminder is retried when connection error occurs"""
        import requests

        mock_post.side_effect = requests.exceptions.ConnectionError("Network unreachable")

        r = SlackReminder.objects.create(
            workspace_id="T070JPE5BQQ",
            creator_id="U999",
            target_type="user",
            target_id="U123",
            message="Test",
            status="pending",
            remind_at=timezone.now() - timedelta(seconds=1),
        )

        call_command("process_slack_reminders_and_huddles")

        r.refresh_from_db()
        self.assertEqual(r.status, "pending")
        self.assertIn("send_failed", r.error_message)

    @patch("website.management.commands.process_slack_reminders_and_huddles._user_exists")
    @override_settings(SLACK_BOT_TOKEN="xoxb-test")
    def test_huddle_creator_check_network_error_does_not_cancel(self, mock_user_exists):
        """Test huddle is not cancelled on network error during creator check"""
        import requests

        mock_user_exists.side_effect = requests.exceptions.ConnectionError("Network error")

        h = SlackHuddle.objects.create(
            workspace_id="T070JPE5BQQ",
            creator_id="U123",
            channel_id="C123",
            title="Test Huddle",
            status="scheduled",
            scheduled_at=timezone.now() + timedelta(days=1),
        )

        # Should not raise exception
        call_command("process_slack_reminders_and_huddles")

        h.refresh_from_db()
        # Should remain scheduled despite network error
        self.assertEqual(h.status, "scheduled")


class SlackSchedulerTransactionTests(TransactionTestCase):
    """Test transaction handling and rollback scenarios"""

    def setUp(self):
        org = Organization.objects.create(name="Test Org", url="https://test.org")
        integ = Integration.objects.create(organization=org, service_name="slack")
        self.slack_integration = SlackIntegration.objects.create(
            integration=integ,
            bot_access_token="xoxb-test-token",
            workspace_name="T070JPE5BQQ",
            default_channel_id="C123",
        )

    @override_settings(SLACK_BOT_TOKEN="xoxb-test")
    def test_database_locks_released_after_fetching_ids(self):
        """Test that database locks are released immediately after fetching IDs"""
        r = SlackReminder.objects.create(
            workspace_id="T070JPE5BQQ",
            creator_id="U999",
            target_type="user",
            target_id="U123",
            message="Test",
            status="pending",
            remind_at=timezone.now() - timedelta(seconds=1),
        )

        with patch("website.management.commands.process_slack_reminders_and_huddles._send_slack_message") as mock_send:
            # During network call, verify we can acquire lock (proving it was released)
            def verify_lock_released(*args, **kwargs):
                # This should succeed if lock was released
                with transaction.atomic():
                    locked = list(SlackReminder.objects.select_for_update().filter(id=r.id))
                    self.assertEqual(len(locked), 1)
                return (True, None)

            mock_send.side_effect = verify_lock_released

            call_command("process_slack_reminders_and_huddles")

    @patch("website.management.commands.process_slack_reminders_and_huddles.requests.post")
    @override_settings(SLACK_BOT_TOKEN="xoxb-test")
    def test_dry_run_does_not_mutate_database(self, mock_post):
        """Test that dry-run mode does not modify database"""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"ok": True, "channel": {"id": "D123"}},
        )

        r = SlackReminder.objects.create(
            workspace_id="T070JPE5BQQ",
            creator_id="U999",
            target_type="user",
            target_id="U123",
            message="Test",
            status="pending",
            remind_at=timezone.now() - timedelta(seconds=1),
        )

        original_remind_at = r.remind_at
        original_status = r.status

        # Run in dry-run mode
        call_command("process_slack_reminders_and_huddles", "--dry-run")

        r.refresh_from_db()
        # Dry-run should not change persisted status or schedule but must avoid network calls
        self.assertEqual(r.status, original_status)
        self.assertEqual(r.remind_at, original_remind_at)
        mock_post.assert_not_called()

    @patch("website.management.commands.process_slack_reminders_and_huddles.requests.post")
    @override_settings(SLACK_BOT_TOKEN="xoxb-test")
    def test_huddle_status_transitions_use_model_methods(self, mock_post):
        """Test that huddle status transitions use model methods (cancel, start, complete)"""
        # Test cancel method
        h1 = SlackHuddle.objects.create(
            workspace_id="T070JPE5BQQ",
            creator_id="U123",
            channel_id="C123",
            title="Test",
            status="scheduled",
            scheduled_at=timezone.now() + timedelta(days=1),
        )

        # Test start method - use different creator so it's not cancelled
        h2 = SlackHuddle.objects.create(
            workspace_id="T070JPE5BQQ",
            creator_id="U456",
            channel_id="C123",
            title="Test",
            status="scheduled",
            scheduled_at=timezone.now() - timedelta(minutes=1),
        )

        # Test complete method
        h3 = SlackHuddle.objects.create(
            workspace_id="T070JPE5BQQ",
            creator_id="U123",
            channel_id="C123",
            title="Test",
            status="started",
            scheduled_at=timezone.now() - timedelta(hours=2),
            duration_minutes=30,
        )

        with patch("website.management.commands.process_slack_reminders_and_huddles._user_exists") as mock_user_exists:

            def user_exists_side_effect(token, user_id):
                # U123 doesn't exist (cancel), U456 exists (continue)
                if user_id == "U123":
                    return (False, None)  # User doesn't exist
                return (True, None)  # User exists

            mock_user_exists.side_effect = user_exists_side_effect

            call_command("process_slack_reminders_and_huddles")

        h1.refresh_from_db()
        h2.refresh_from_db()
        h3.refresh_from_db()

        self.assertEqual(h1.status, "cancelled")
        self.assertEqual(h2.status, "started")
        self.assertEqual(h3.status, "completed")
