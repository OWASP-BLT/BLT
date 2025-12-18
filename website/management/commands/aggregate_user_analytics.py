from datetime import timedelta

from django.core.management.base import CommandError
from django.db import DatabaseError
from django.utils import timezone

from website.management.base import LoggedBaseCommand
from website.models import UserActivity


class Command(LoggedBaseCommand):
    help = "Clean up (delete) UserActivity records older than 90 days to enforce data retention"

    def handle(self, *args, **options):
        """Clean up old UserActivity records."""
        try:
            # Calculate cutoff date (90 days ago)
            cutoff_date = timezone.now() - timedelta(days=90)

            # Query old activity records
            old_activities = UserActivity.objects.filter(timestamp__lt=cutoff_date)

            # Get count before deletion
            count = old_activities.count()

            if count == 0:
                self.stdout.write(self.style.WARNING("No UserActivity records older than 90 days found"))
                return

            # Delete old records
            deleted_count, _ = old_activities.delete()

            # Output success message
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully deleted {deleted_count} UserActivity records older than {cutoff_date.date()}"
                )
            )

        except DatabaseError as e:
            error_message = f"Failed to clean up UserActivity records: {str(e)}"
            self.stderr.write(self.style.ERROR(error_message))
            raise CommandError(error_message)
