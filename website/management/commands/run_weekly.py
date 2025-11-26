import logging

from django.core import management
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs commands scheduled to execute weekly"

    def handle(self, *args, **options):
        logger.info(f"Starting weekly scheduled tasks at {timezone.now()}")

        # Send weekly bug report digest to organization followers
        try:
            management.call_command("send_weekly_bug_digest")
            logger.info("Completed weekly bug digest emails")
        except Exception as e:
            logger.error(f"Error sending weekly bug digest: {str(e)}")

        # Clean up old sample invite records (older than 7 days)
        try:
            management.call_command("cleanup_sample_invites", days=7)
            logger.info("Completed sample invites cleanup")
        except Exception as e:
            logger.error(f"Error cleaning up sample invites: {str(e)}")
