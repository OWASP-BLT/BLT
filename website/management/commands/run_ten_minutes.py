import logging

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs commands scheduled to execute 10 minutes"

    def handle(self, *args, **options):
        try:
            logger.info(f"Starting 10 minute scheduled tasks at {timezone.now()}")
            try:
                call_command("cron_send_reminders")
            except Exception as e:
                logger.error("Error sending user reminders", exc_info=True)
        except Exception as e:
            logger.error("Error in 10 minute tasks", exc_info=True)
            raise
