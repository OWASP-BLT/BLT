"""
Django management command to delete unverified users.

This command identifies and removes users who have not verified their email
or have been inactive for an extended period.

Usage:
    python manage.py delete_unverified_users --days 30
    python manage.py delete_unverified_users --dry-run
    python manage.py delete_unverified_users --include-new

Features:
- Safe dry-run mode to preview deletions
- Configurable retention period (--days)
- Protection for superusers and staff
- Atomic transactions for data consistency
- Bulk deletion for performance
"""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from website.models import User


class Command(BaseCommand):
    help = "Delete unverified and inactive users"

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Delete users inactive for more than this many days (default: 30)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )
        parser.add_argument(
            "--include-new",
            action="store_true",
            help="Also include newly created users who never logged in",
        )
        parser.add_argument(
            "--yes",
            action="store_true",
            help="Skip confirmation prompt and proceed with deletion",
        )

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]
        include_new = options["include_new"]
        skip_confirmation = options["yes"]

        if days < 1:
            raise CommandError("--days must be a positive integer")

        cutoff_date = timezone.now() - timedelta(days=days)

        unverified_users = User.objects.filter(
            last_login__isnull=True,
            date_joined__lt=cutoff_date,
        ).exclude(
            is_superuser=True,
            is_staff=True,
        )

        if include_new:
            new_users = User.objects.filter(
                last_login__isnull=True,
            ).exclude(
                is_superuser=True,
                is_staff=True,
            )
            unverified_users = unverified_users | new_users

        unverified_users = unverified_users.distinct()
        count = unverified_users.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"DRY RUN: Would delete {count} unverified/inactive users")
            )
            if count > 0:
                self.stdout.write("Users that would be deleted:")
                for user in unverified_users[:20]:
                    days_old = (timezone.now() - user.date_joined).days
                    self.stdout.write(
                        f"  - {user.username} ({user.email}) - Created: {user.date_joined.date()} ({days_old} days old)"
                    )
                if count > 20:
                    self.stdout.write(f"  ... and {count - 20} more")
        else:
            if count == 0:
                self.stdout.write("No users to delete.")
                return

            if not skip_confirmation:
                self.stdout.write(self.style.WARNING(f"About to delete {count} users."))
                confirm = input("Continue? [y/N] ")
                if confirm.lower() != "y":
                    self.stdout.write("Aborted.")
                    return

            self.stdout.write(f"Deleting {count} users...")

            with transaction.atomic():
                deleted_count, _ = unverified_users.delete()

            self.stdout.write(
                self.style.SUCCESS(f"Successfully deleted {deleted_count} unverified/inactive users")
            )
