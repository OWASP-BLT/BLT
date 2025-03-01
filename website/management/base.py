from django.core.management.base import BaseCommand
from django.utils import timezone

from website.models import ManagementCommandLog


class LoggedBaseCommand(BaseCommand):
    """Base command class that logs execution time and status."""

    def execute(self, *args, **options):
        command_name = self.__class__.__module__.split(".")[-1]
        try:
            result = super().execute(*args, **options)

            # First try to get existing log
            log_entry = ManagementCommandLog.objects.filter(command_name=command_name).first()

            if log_entry:
                # Update existing entry
                log_entry.success = True
                log_entry.last_run = timezone.now()
                log_entry.error_message = ""
                log_entry.run_count = log_entry.run_count + 1
                log_entry.save()
            else:
                # Create new entry
                ManagementCommandLog.objects.create(
                    command_name=command_name, success=True, run_count=1, last_run=timezone.now()
                )

            return result
        except Exception as e:
            # Handle error case
            log_entry = ManagementCommandLog.objects.filter(command_name=command_name).first()

            if log_entry:
                # Update existing entry
                log_entry.success = False
                log_entry.last_run = timezone.now()
                log_entry.error_message = str(e)
                log_entry.run_count = log_entry.run_count + 1
                log_entry.save()
            else:
                # Create new entry
                ManagementCommandLog.objects.create(
                    command_name=command_name, success=False, error_message=str(e), run_count=1, last_run=timezone.now()
                )

            raise
