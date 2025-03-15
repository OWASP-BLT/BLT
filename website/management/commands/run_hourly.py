import logging

from django.core import management
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs commands scheduled to execute hourly"

    def handle(self, *args, **options):
        try:
            logger.info(f"Starting hourly scheduled tasks at {timezone.now()}")

            # Run the dynamic repository update command
            # This will update repositories based on their GitHub issue activity dates
            # and fetch issues with $ in tags and closed pull requests
            management.call_command("update_repos_dynamic")

            # Other hourly commands can be added here
            # management.call_command('other_hourly_command')
        except Exception as e:
            logger.error(f"Error in hourly tasks: {e}")
            raise

