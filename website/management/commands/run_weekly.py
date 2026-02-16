import logging

from django.core import management
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)

# Commands to run weekly, in order
WEEKLY_COMMANDS = [
    ("send_weekly_bug_digest", "sending weekly bug digest"),
    ("cleanup_sample_invites", "cleaning up sample invites", {"days": 7}),
    ("slack_weekly_report", "sending weekly Slack report"),
]


class Command(BaseCommand):
    help = "Runs commands scheduled to execute weekly"

    def handle(self, *args, **options):
        logger.info(f"Starting weekly scheduled tasks at {timezone.now()}")

        succeeded = 0
        failed = 0

        for entry in WEEKLY_COMMANDS:
            command_name = entry[0]
            description = entry[1]
            kwargs = entry[2] if len(entry) > 2 else {}

            try:
                management.call_command(command_name, **kwargs)
                logger.info(f"Completed {description}")
                succeeded += 1
            except Exception:
                logger.exception(f"Error {description}")
                failed += 1

        logger.info(f"Weekly tasks complete: {succeeded} succeeded, {failed} failed")
