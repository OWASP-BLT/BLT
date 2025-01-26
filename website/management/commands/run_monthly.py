import logging

from django.core.management.base import BaseCommand

# from django.core import management
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs commands scheduled to execute monthly"

    def handle(self, *args, **options):
        try:
            logger.info(f"Starting monthly scheduled tasks at {timezone.now()}")

            # Add commands to be executed monthly
            # management.call_command('monthly_command1')
            # management.call_command('monthly_command2')
        except Exception as e:
            logger.error(f"Error in monthly tasks: {str(e)}")
            raise
