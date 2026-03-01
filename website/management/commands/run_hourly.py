import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs commands scheduled to execute hourly"

    def handle(self, *args, **options):
        try:
            logger.info(f"Starting hourly scheduled tasks at {timezone.now()}")

            # Repository updates have been disabled from automatic scheduling.
            # Updates are now triggered manually by logged-in users via the
            # "Refresh from GitHub" button on the repository detail page.

            # Other hourly commands can be added here
            # management.call_command('other_hourly_command')
        except Exception:
            logger.exception("Error in hourly tasks")
            raise
