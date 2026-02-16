from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone


class Command(BaseCommand):
    help = "Delete user accounts that have not verified their email address within the specified period"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Delete unverified users older than this many days (default: 30)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )

    def handle(self, *_, **options):
        days = options["days"]
        dry_run = options["dry_run"]
        cutoff_date = timezone.now() - timedelta(days=days)

        # Find users who joined before the cutoff and have no verified email.
        # Uses django-allauth's EmailAddress model via reverse relation.
        # Staff and superusers are always preserved as a safety measure.
        unverified_users = User.objects.filter(
            date_joined__lt=cutoff_date,
            is_staff=False,
            is_superuser=False,
        ).exclude(
            emailaddress__verified=True,
        )

        count = unverified_users.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would delete {count} unverified users who joined more than {days} days ago"
                )
            )
            if count > 0:
                self.stdout.write("Users that would be deleted:")
                for user in unverified_users[:10]:
                    self.stdout.write(f"  - {user.username} (joined: {user.date_joined})")
                if count > 10:
                    self.stdout.write(f"  ... and {count - 10} more")
        else:
            unverified_users.delete()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully deleted {count} unverified users who joined more than {days} days ago"
                )
            )
