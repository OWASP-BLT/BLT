import logging

from django.core.management.base import BaseCommand

# from django.core import management
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs commands scheduled to execute weekly"

    def handle(self, *args, **options):
        try:
            logger.info(f"Starting weekly scheduled tasks at {timezone.now()}")

            # Add commands to be executed weekly
            # management.call_command('weekly_command1')
            # management.call_command('weekly_command2')
        except Exception as e:
            logger.error(f"Error in weekly tasks: {str(e)}")
            raise
