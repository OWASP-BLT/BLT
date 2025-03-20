from django.core.management.base import BaseCommand
from django.utils import timezone

from website.models import DailyStats, ManagementCommandLog


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

            # Update DailyStats for this command
            today = timezone.now().date()
            try:
                # Try to find an existing entry for today
                daily_stat = DailyStats.objects.get(name=command_name, created__date=today)
                # Increment the value
                try:
                    current_value = int(daily_stat.value)
                    daily_stat.value = str(current_value + 1)
                except (ValueError, TypeError):
                    daily_stat.value = "1"
                daily_stat.save()
            except DailyStats.DoesNotExist:
                # Create a new entry
                DailyStats.objects.create(name=command_name, value="1")

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

            # Still update DailyStats even if there was an error
            today = timezone.now().date()
            try:
                daily_stat = DailyStats.objects.get(name=command_name, created__date=today)
                # Increment the value
                try:
                    current_value = int(daily_stat.value)
                    daily_stat.value = str(current_value + 1)
                except (ValueError, TypeError):
                    daily_stat.value = "1"
                daily_stat.save()
            except DailyStats.DoesNotExist:
                # Create a new entry
                DailyStats.objects.create(name=command_name, value="1")

            raise
