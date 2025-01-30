import logging

from django.core.management.base import BaseCommand

# from django.core import management
from django.utils import timezone

from website import management

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs commands scheduled to execute daily"

    def handle(self, *args, **options):
        try:
            logger.info(f"Starting daily scheduled tasks at {timezone.now()}")
            management.call_command("update_github_issues")
            management.call_command("fetch_contributor_stats")
        except Exception as e:
            logger.error(f"Error in daily tasks: {str(e)}")
            raise
