import logging
from datetime import timedelta

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from website.models import SlackHuddle, SlackIntegration, SlackReminder

logger = logging.getLogger(__name__)

SLACK_API_BASE = "https://slack.com/api"
MAX_RETRIES = 5
BASE_BACKOFF_SECONDS = 60  # 1 minute base
MAX_RETRY_AGE_DAYS = 7  # Stop retrying reminders older than this


def _slack_headers(token: str):
    sanitized_token = token.replace("\r", "").replace("\n", "")
    return {
        "Authorization": f"Bearer {sanitized_token}",
        "Content-Type": "application/json; charset=utf-8",
    }


def _resolve_channel_id(token: str, target_id: str) -> tuple[str | None, int | None]:
    """
    Resolve a DM channel for user IDs; pass channels as-is.
    - User IDs typically start with 'U'/'W'
    - Channel IDs typically start with 'C'
    """
    if not target_id:
        return None, None
    if target_id.startswith(("C", "G")):
        return target_id, None

    # Open a DM channel with the user
    try:
        resp = requests.post(
            f"{SLACK_API_BASE}/conversations.open",
            headers=_slack_headers(token),
            json={"users": [target_id]},
            timeout=8,
        )
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "0") or 0)
            return None, retry_after
        data = resp.json()
        if data.get("ok") and data.get("channel", {}).get("id"):
            return data["channel"]["id"], None
        logger.warning("Slack conversations.open failed: %s", data.get("error"))
    except Exception as e:
        logger.error("Slack conversations.open error", exc_info=True)
    return None, None


def _send_slack_message(token: str, target_id: str, text: str, thread_ts: str | None = None) -> tuple[bool, int | None]:
    channel_id, retry_after = _resolve_channel_id(token, target_id)
    if not channel_id:
        return False, retry_after
    payload = {"channel": channel_id, "text": text}
    if thread_ts:
        payload["thread_ts"] = thread_ts
    try:
        resp = requests.post(
            f"{SLACK_API_BASE}/chat.postMessage",
            headers=_slack_headers(token),
            json=payload,
            timeout=8,
        )
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "0") or 0)
            logger.warning("Slack chat.postMessage rate limited. Retry-After=%s", retry_after)
            return False, retry_after
        data = resp.json()
        if data.get("ok"):
            return True, None
        logger.warning("Slack chat.postMessage failed: %s", data.get("error"))
        return False, None
    except Exception:
        logger.error("Slack chat.postMessage error", exc_info=True)
        return False, None


def _parse_retry_count(error_message: str | None) -> int:
    if not error_message:
        return 0
    try:
        # Expecting a string like "retries=2; last_error=..."
        for part in str(error_message).split(";"):
            part = part.strip()
            if part.startswith("retries="):
                return int(part.split("=", 1)[1])
    except Exception:
        return 0
    return 0


def _format_error(error: str, retries: int) -> str:
    return f"retries={retries}; last_error={error}"


def _user_exists(token: str, user_id: str) -> tuple[bool, int | None]:
    """Check if a Slack user exists and is active in the workspace.

    Returns (exists, retry_after). If rate limited or network error, returns (False, retry_after).
    If user not found (404), returns (False, None).
    """
    try:
        # Users typically start with 'U' or 'W'
        if not user_id or not user_id.startswith(("U", "W")):
            return False, None
        resp = requests.post(
            f"{SLACK_API_BASE}/users.info",
            headers=_slack_headers(token),
            json={"user": user_id},
            timeout=8,
        )
        if resp.status_code == 429:
            retry_after = int(resp.headers.get("Retry-After", "0") or 0)
            return False, retry_after
        data = resp.json()
        if data.get("ok"):
            # Consider deleted or deactivated users as non-existent for messaging
            user = data.get("user", {})
            if user.get("deleted") or user.get("is_restricted", False) or user.get("is_ultra_restricted", False):
                return False, None
            return True, None
        # Common errors: user_not_found, account_inactive
        return False, None
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        # Network errors should be retried, not treated as user not found
        logger.error("Slack users.info error", exc_info=True)
        return False, 1  # Return 1 to indicate retry needed
    except Exception:
        logger.error("Slack users.info error", exc_info=True)
        return False, None


class Command(BaseCommand):
    help = "Process Slack reminders and huddles (send pending reminders, notify upcoming huddles, update statuses)"

    def add_arguments(self, parser):
        parser.add_argument("--window-minutes", type=int, default=15, help="Pre-huddle notify window in minutes")
        parser.add_argument("--batch-size", type=int, default=50, help="Max records per batch for each type")
        parser.add_argument("--dry-run", action="store_true", help="Log actions without sending messages")

    def handle(self, *args, **options):
        token = getattr(settings, "SLACK_BOT_TOKEN", None)
        if not token and not options["dry_run"]:
            logger.error("SLACK_BOT_TOKEN not configured; aborting send")
            return

        window = timedelta(minutes=options["window_minutes"])
        now = timezone.now()

        self._process_reminders(token, now, options)
        self._process_huddles(token, now, window, options)

    def _token_for_workspace(self, workspace_id: str, default_token: str | None):
        integ = SlackIntegration.objects.filter(workspace_id=workspace_id).first()
        return integ.bot_access_token if integ and integ.bot_access_token else default_token

    def _process_reminders(self, token: str | None, now, options):
        # Step 1: Fetch reminder IDs inside transaction (release lock quickly)
        with transaction.atomic():
            reminder_ids = list(
                SlackReminder.objects.select_for_update(skip_locked=True)
                .filter(status="pending", remind_at__lte=now)
                .order_by("remind_at")
                .values_list("id", flat=True)[: options["batch_size"]]
            )

        if not reminder_ids:
            logger.info("No due SlackReminder records")
            return

        # Step 2: Load full reminder objects (no locks held)
        reminders = SlackReminder.objects.filter(id__in=reminder_ids).select_related()
        workspace_ids = {r.workspace_id for r in reminders}
        integrations = SlackIntegration.objects.filter(workspace_id__in=workspace_ids)
        token_map = {i.workspace_id: i.bot_access_token for i in integrations if i.bot_access_token}

        # Step 3: Process each reminder (make network calls without holding locks)
        for reminder in reminders:
            try:
                # pick correct token per workspace
                ws_token = token_map.get(reminder.workspace_id, token)
                if not ws_token and not options["dry_run"]:
                    # cannot send without any token
                    with transaction.atomic():
                        r = SlackReminder.objects.select_for_update().filter(id=reminder.id, status="pending").first()
                        if r:
                            r.status = "failed"
                            r.error_message = _format_error("no_token", _parse_retry_count(r.error_message))
                            if not options["dry_run"]:
                                r.save(update_fields=["status", "error_message"])
                    continue

                # If target is a user, ensure they still exist; avoid silent failures (network call)
                target_type = getattr(reminder, "target_type", None)
                if not options["dry_run"] and target_type == "user" and reminder.target_id:
                    exists, retry_after_exists = _user_exists(ws_token, reminder.target_id)
                    if not exists and retry_after_exists is None:
                        with transaction.atomic():
                            r = (
                                SlackReminder.objects.select_for_update()
                                .filter(id=reminder.id, status="pending")
                                .first()
                            )
                            if r:
                                r.status = "failed"
                                r.error_message = _format_error("user_not_found", _parse_retry_count(r.error_message))
                                if not options["dry_run"]:
                                    r.save(update_fields=["status", "error_message"])
                        continue

                msg = reminder.message or ""
                target = reminder.target_id

                # Make network call outside transaction
                if options["dry_run"]:
                    sent, retry_after = True, None
                else:
                    sent, retry_after = _send_slack_message(ws_token, target, msg)

                # Step 4: Re-acquire lock to update status
                with transaction.atomic():
                    r = SlackReminder.objects.select_for_update().filter(id=reminder.id, status="pending").first()
                    if not r:
                        logger.warning("SlackReminder id=%s no longer pending, skipping update", reminder.id)
                        continue

                    # Check if reminder is too old to retry (prevent unbounded retry loops)
                    if r.created_at and (timezone.now() - r.created_at).days > MAX_RETRY_AGE_DAYS:
                        r.status = "failed"
                        r.error_message = _format_error("max_age_exceeded", _parse_retry_count(r.error_message))
                        if not options["dry_run"]:
                            r.save(update_fields=["status", "error_message"])
                        continue

                    if sent:
                        r.status = "sent"
                        r.sent_at = timezone.now()
                        r.error_message = ""
                    else:
                        # retry with exponential backoff capped by MAX_RETRIES
                        current_retries = _parse_retry_count(r.error_message)
                        next_retries = current_retries + 1
                        if next_retries <= MAX_RETRIES:
                            # Prefer Slack-provided Retry-After for rate limits
                            if retry_after and retry_after > 0:
                                delay_seconds = retry_after
                            else:
                                delay_seconds = min(BASE_BACKOFF_SECONDS * (2 ** (next_retries - 1)), 60 * 60)
                            r.remind_at = timezone.now() + timedelta(seconds=delay_seconds)
                            r.status = "pending"
                            r.error_message = _format_error("send_failed", next_retries)
                        else:
                            r.status = "failed"
                            r.error_message = _format_error("max_retries_exceeded", next_retries - 1)
                    if not options["dry_run"]:
                        r.save(update_fields=["status", "sent_at", "error_message", "remind_at"])
            except Exception:
                logger.error("Failed processing SlackReminder id=%s", reminder.id, exc_info=True)

    def _process_huddles(self, token: str | None, now, window, options):
        # First, cancel huddles whose creator has left the workspace to avoid orphans
        # Only check huddles scheduled within the next 7 days to avoid processing old records
        future_cutoff = now + timedelta(days=7)

        # Fetch huddle IDs to check (release locks quickly)
        with transaction.atomic():
            cancel_ids = list(
                SlackHuddle.objects.select_for_update(skip_locked=True)
                .filter(status="scheduled", scheduled_at__lte=future_cutoff)
                .order_by("scheduled_at")
                .values_list("id", flat=True)[: options["batch_size"]]
            )

        # Process cancellations (make network calls without holding locks)
        for huddle_id in cancel_ids:
            try:
                huddle = SlackHuddle.objects.filter(id=huddle_id).first()
                if not huddle or huddle.status != "scheduled":
                    continue

                ws_token = self._token_for_workspace(huddle.workspace_id, token)
                if not ws_token:
                    continue

                # Network call outside transaction
                exists, retry_after_exists = _user_exists(ws_token, huddle.creator_id)
                # Only cancel if user truly doesn't exist (404), not on rate limits or network errors
                if not exists and retry_after_exists is None:
                    # Re-acquire lock to update status
                    with transaction.atomic():
                        h = SlackHuddle.objects.select_for_update().filter(id=huddle_id, status="scheduled").first()
                        if h and not options["dry_run"]:
                            # Use model method to maintain business logic consistency
                            h.cancel()
                elif retry_after_exists:
                    # Rate limited - log and skip for now, will retry on next run
                    logger.info("Rate limited checking creator for huddle id=%s, will retry later", huddle_id)
            except Exception:
                logger.error("Failed creator check for SlackHuddle id=%s", huddle_id, exc_info=True)

        # Notify participants for upcoming huddles not yet reminded
        # Fetch huddle IDs (release locks quickly)
        with transaction.atomic():
            upcoming_ids = list(
                SlackHuddle.objects.select_for_update(skip_locked=True)
                .filter(status="scheduled", reminder_sent=False, scheduled_at__lte=now + window)
                .order_by("scheduled_at")
                .values_list("id", flat=True)[: options["batch_size"]]
            )

        # Load huddles without locks and process notifications
        upcoming_huddles = SlackHuddle.objects.filter(id__in=upcoming_ids).prefetch_related("participants")

        for huddle in upcoming_huddles:
            try:
                # Skip if already reminded (race condition check)
                if huddle.reminder_sent or huddle.status != "scheduled":
                    continue

                participants = []
                # Try different shapes to stay compatible with existing model
                if hasattr(huddle, "participant_ids") and huddle.participant_ids:
                    participants = list(huddle.participant_ids)
                elif hasattr(huddle, "participants"):
                    # ManyToMany relation expected to have 'user_id'
                    participants = [getattr(p, "user_id", None) for p in huddle.participants.all()]

                participants = [p for p in participants if p]

                # If no participants, mark as reminded to avoid infinite retries
                if not participants:
                    if options["dry_run"]:
                        logger.info("DRY-RUN huddle=%s has no participants; marking as reminded", huddle.id)
                    else:
                        SlackHuddle.objects.filter(id=huddle.id, reminder_sent=False).update(reminder_sent=True)
                        logger.info("Huddle id=%s has no participants; marking reminder_sent to avoid reprocessing", huddle.id)
                    continue

                title = getattr(huddle, "title", "Huddle")
                title = title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                start_at = timezone.localtime(huddle.scheduled_at).strftime("%Y-%m-%d %H:%M")
                channel_id = getattr(huddle, "channel_id", None)

                # Compose a concise pre-notification
                text = f"⏰ Reminder: '{title}' starts at {start_at}. Join the huddle in the channel."

                ok_count = 0
                if options["dry_run"]:
                    logger.info("DRY-RUN huddle=%s notify %d participants", huddle.id, len(participants))
                else:
                    ws_token = self._token_for_workspace(huddle.workspace_id, token)
                    if not ws_token:
                        # Mark as reminded to prevent infinite retry loop
                        # Admins must configure token and manually reset if needed
                        with transaction.atomic():
                            h = (
                                SlackHuddle.objects.select_for_update()
                                .filter(id=huddle.id, reminder_sent=False)
                                .first()
                            )
                            if h:
                                h.reminder_sent = True
                                if not options["dry_run"]:
                                    h.save(update_fields=["reminder_sent"])
                        logger.warning(
                            "No Slack token for workspace=%s; marking huddle id=%s as reminded "
                            "(notifications not sent; configure token and reset manually if needed)",
                            huddle.workspace_id,
                            huddle.id,
                        )
                        continue

                    # Make network calls outside transaction
                    for pid in participants:
                        exists, retry_after_exists = _user_exists(ws_token, pid)
                        if not exists and not retry_after_exists:
                            continue
                        if _send_slack_message(ws_token, pid, text)[0]:
                            ok_count += 1
                    # Also drop a message in the channel if available
                    if channel_id:
                        _send_slack_message(ws_token, channel_id, f"📣 Huddle '{title}' will start at {start_at}")

                # Re-acquire lock to mark as reminded only if at least one notification succeeded
                with transaction.atomic():
                    h = SlackHuddle.objects.select_for_update().filter(id=huddle.id, reminder_sent=False).first()
                    if h:
                        # Only mark as reminded if at least one participant was notified successfully
                        if ok_count > 0:
                            h.reminder_sent = True
                            if not options["dry_run"]:
                                h.save(update_fields=["reminder_sent"])

            except Exception:
                logger.error("Failed pre-notify for SlackHuddle id=%s", huddle.id, exc_info=True)

        # Transition started huddles (no network calls, but keep transactions short)
        with transaction.atomic():
            to_start = (
                SlackHuddle.objects.select_for_update(skip_locked=True)
                .filter(status="scheduled", scheduled_at__lte=now)
                .order_by("scheduled_at")[: options["batch_size"]]
            )
            for h in to_start:
                try:
                    # Skip state changes during dry-run to avoid persisting mutations
                    if not options["dry_run"]:
                        # Use model method to maintain business logic consistency
                        h.start()
                except Exception:
                    logger.error("Failed to mark SlackHuddle started id=%s", h.id, exc_info=True)

        # Transition completed huddles (started and duration elapsed)
        with transaction.atomic():
            to_complete = (
                SlackHuddle.objects.select_for_update(skip_locked=True)
                .filter(status="started")
                .order_by("scheduled_at")[: options["batch_size"]]
            )
            for h in to_complete:
                try:
                    end_at = h.scheduled_at + timedelta(minutes=h.duration_minutes)
                    if end_at <= now and not options["dry_run"]:
                        # Use model method to maintain business logic consistency
                        h.complete()
                except Exception:
                    logger.error("Failed to mark SlackHuddle completed id=%s", h.id, exc_info=True)
