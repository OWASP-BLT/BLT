import logging

from django.core.management.base import BaseCommand

# from django.core import management
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs commands scheduled to execute hourly"

    def handle(self, *args, **options):
        try:
            logger.info(f"Starting hourly scheduled tasks at {timezone.now()}")

            # We can add hourly commands here
            # management.call_command('hourly_command1')
            # management.call_command('hourly_command2')
        except Exception as e:
            logger.error(f"Error in hourly tasks: {str(e)}")
            raise
