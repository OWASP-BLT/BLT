import logging

from django.core import management
from django.core.management.base import BaseCommand
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs commands scheduled to execute monthly"

    def handle(self, *args, **options):
        try:
            logger.info(f"Starting monthly scheduled tasks at {timezone.now()}")

            # Award BACON tokens to top users for the month
            management.call_command("reward_top_users")
        except Exception as e:
            logger.error(f"Error in monthly tasks: {str(e)}")
            raise
