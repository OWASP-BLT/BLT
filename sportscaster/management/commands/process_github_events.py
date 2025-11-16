import logging
import time

from django.core.management.base import BaseCommand

from sportscaster.services import EventProcessingService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Process GitHub events for monitored entities"

    def add_arguments(self, parser):
        parser.add_argument(
            "--continuous",
            action="store_true",
            help="Run continuously in a loop",
        )
        parser.add_argument(
            "--interval",
            type=int,
            default=60,
            help="Interval in seconds between runs (default: 60)",
        )

    def handle(self, *args, **options):
        continuous = options["continuous"]
        interval = options["interval"]

        service = EventProcessingService()

        self.stdout.write(self.style.SUCCESS("Starting GitHub event processing..."))

        if continuous:
            self.stdout.write(
                self.style.SUCCESS(f"Running in continuous mode with {interval} second intervals. Press Ctrl+C to stop.")
            )
            try:
                while True:
                    self._process_events(service)
                    time.sleep(interval)
            except KeyboardInterrupt:
                self.stdout.write(self.style.SUCCESS("\nStopping event processing..."))
        else:
            self._process_events(service)

        self.stdout.write(self.style.SUCCESS("Event processing complete."))

    def _process_events(self, service):
        """Process events and handle errors"""
        try:
            service.process_monitored_entities()
            self.stdout.write(
                self.style.SUCCESS(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Processed monitored entities")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error processing events: {e}"))
            logger.error(f"Error in process_github_events command: {e}", exc_info=True)
