from datetime import timedelta

from django.utils import timezone

from website.management.base import LoggedBaseCommand
from website.models import User


class Command(LoggedBaseCommand):
    help = "Update user status based on activity"

    def handle(self, *args, **options):
        inactive_threshold = timezone.now() - timedelta(days=30)
        updated = User.objects.filter(last_login__lt=inactive_threshold, is_active=True).update(is_active=False)

        self.stdout.write(f"Deactivated {updated} inactive users.")
