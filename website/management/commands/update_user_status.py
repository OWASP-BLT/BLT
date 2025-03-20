from django.utils import timezone

from website.management.base import LoggedBaseCommand
from website.models import User


class Command(LoggedBaseCommand):
    help = "Update user status based on activity"

    def handle(self, *args, **options):
        # Get all users who haven't logged in for 30 days
        inactive_threshold = timezone.now() - timezone.timedelta(days=30)
        users = User.objects.filter(last_login__lt=inactive_threshold)

        for user in users:
            user.is_active = False
            user.save()
            self.stdout.write(f"Deactivated user: {user.username}")

        self.stdout.write("User status update completed")
