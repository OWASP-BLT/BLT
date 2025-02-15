from django.core.management.base import BaseCommand
from django.db.models import F

from website.models import ManagementCommandLog


class LoggedBaseCommand(BaseCommand):
    """Base command class that logs execution time and status."""

    def execute(self, *args, **options):
        command_name = self.__class__.__module__.split(".")[-1]
        try:
            result = super().execute(*args, **options)
            ManagementCommandLog.objects.update_or_create(
                command_name=command_name, defaults={"success": True, "run_count": F("run_count") + 1}
            )
            return result
        except Exception as e:
            ManagementCommandLog.objects.update_or_create(
                command_name=command_name,
                defaults={"success": False, "error_message": str(e), "run_count": F("run_count") + 1},
            )
            raise
