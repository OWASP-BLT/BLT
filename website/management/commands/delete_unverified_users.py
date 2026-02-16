from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
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

        if days <= 0:
            raise CommandError("--days must be a positive integer")

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

        if dry_run:
            count = unverified_users.count()
            label = "user" if count == 1 else "users"
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would delete {count} unverified {label} who joined more than {days} days ago"
                )
            )
            if count > 0:
                self.stdout.write("Users that would be deleted:")
                for user in unverified_users[:10]:
                    self.stdout.write(f"  - {user.username} (joined: {user.date_joined})")
                if count > 10:
                    self.stdout.write(f"  ... and {count - 10} more")
        else:
            deleted_count, _ = unverified_users.delete()
            label = "user" if deleted_count == 1 else "users"
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully deleted {deleted_count} unverified {label} who joined more than {days} days ago"
                )
            )
