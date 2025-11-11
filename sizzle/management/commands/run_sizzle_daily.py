import logging

from django.core.management import call_command
from django.utils import timezone

from sizzle.management.base import SizzleBaseCommand

logger = logging.getLogger(__name__)


class Command(SizzleBaseCommand):
    help = "Runs all Sizzle-related commands scheduled to execute daily"

    def handle(self, *args, **options):
        try:
            self.log_info(f"Starting daily Sizzle tasks at {timezone.now()}")
            
            # Run daily check-in reminders
            try:
                self.log_info("Running daily check-in reminders...")
                call_command("daily_checkin_reminder")
                self.log_info("Daily check-in reminders completed successfully")
            except Exception as e:
                self.log_error(f"Error sending daily checkin reminders: {str(e)}")
            
            # Run email reminders based on user settings
            try:
                self.log_info("Running email reminder system...")
                call_command("cron_send_reminders")
                self.log_info("Email reminder system completed successfully")
            except Exception as e:
                self.log_error(f"Error sending user reminders: {str(e)}")
                
            self.log_info("All daily Sizzle tasks completed")
            
        except Exception as e:
            self.log_error(f"Critical error in daily Sizzle tasks: {str(e)}")
            raise