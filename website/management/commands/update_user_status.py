from datetime import timedelta

from django.utils import timezone

from website.management.base import LoggedBaseCommand
from website.models import User


class Command(LoggedBaseCommand):
    help = "Update user status based on activity"

    def handle(self, *args, **options):
        # Get all users who haven't logged in for 30 days
        inactive_threshold = timezone.now() - timedelta(days=30)
        inactive_users = User.objects.filter(last_login__lt=inactive_threshold, is_active=True)

        count = inactive_users.update(is_active=False)
        self.stdout.write(f"Deactivated {count} inactive users")

        self.stdout.write("User status update completed")
