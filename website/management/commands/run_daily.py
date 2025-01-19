import logging

from django.core.management.base import BaseCommand

# from django.core import management
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs commands scheduled to execute daily"

    def handle(self, *args, **options):
        try:
            logger.info(f"Starting daily scheduled tasks at {timezone.now()}")

            # Add commands to be executed daily
            # management.call_command('daily_command1')
            # management.call_command('daily_command2')
        except Exception as e:
            logger.error(f"Error in daily tasks: {str(e)}")
            raise
