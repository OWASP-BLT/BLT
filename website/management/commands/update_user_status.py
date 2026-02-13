from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from website.management.base import LoggedBaseCommand
from website.models import User


class Command(LoggedBaseCommand):
    help = "Update user status based on activity"

    def handle(self, *args, **options):
        inactive_threshold = timezone.now() - timedelta(days=30)
        updated = (
            User.objects.filter(is_active=True)
            .filter(
                Q(last_login__lt=inactive_threshold)
                | Q(last_login__isnull=True, date_joined__lt=inactive_threshold)
            )
            .update(is_active=False)
        )

        self.stdout.write(self.style.SUCCESS(f"Deactivated {updated} inactive users."))
