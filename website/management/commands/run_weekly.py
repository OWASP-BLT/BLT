import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs commands scheduled to execute weekly"

    def handle(self, *args, **options):
        try:
            logger.info(f"Starting weekly scheduled tasks at {timezone.now()}")

            # Send weekly Slack reports to organizations with Slack integration
            try:
                call_command("slack_weekly_report")
            except Exception as e:
                logger.error("Error sending weekly Slack reports", exc_info=True)

            # Add other weekly commands here
            try:
                call_command('cleanup_sample_invites', days=7)
            except Exception as e:
                logger.error("Error in sample invites cleanup", exc_info=True)

        except Exception as e:
            logger.error("Error in weekly tasks", exc_info=True)
            raise
