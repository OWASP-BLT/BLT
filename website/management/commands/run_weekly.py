import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from website.tasks import send_weekly_stats

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Runs commands scheduled to execute weekly"

    def handle(self, *args, **options):
        try:
            logger.info(f"Starting weekly scheduled tasks at {timezone.now()}")

            # Trigger the weekly stats delivery task
            self.stdout.write("Triggering weekly stats delivery...")
            result = send_weekly_stats.delay()
            self.stdout.write(self.style.SUCCESS(f"Weekly stats task queued with ID: {result.id}"))

            logger.info("Weekly scheduled tasks completed successfully")
        except Exception as e:
            logger.error(f"Error in weekly tasks: {str(e)}")
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
            raise
