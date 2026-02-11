"""
Django management command to delete unverified users.

This command identifies and removes users who have not verified their email
or have been inactive for an extended period.

Usage:
    python manage.py delete_unverified_users --days 30
    python manage.py delete_unverified_users --dry-run
"""

from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
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

    def handle(self, *args, **options):
        days = options["days"]
        dry_run = options["dry_run"]
        include_new = options["include_new"]

        cutoff_date = timezone.now() - timedelta(days=days)

        # Find unverified users: users who have never logged in and were created before cutoff
        unverified_users = User.objects.filter(
            last_login__isnull=True,
            date_joined__lt=cutoff_date,
        )

        # Also find very old inactive users (never logged in since creation)
        if include_new:
            new_users = User.objects.filter(
                last_login__isnull=True,
            )
            unverified_users = new_users

        count = unverified_users.count()

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"DRY RUN: Would delete {count} unverified/inactive users")
            )
            if count > 0:
                self.stdout.write("Users that would be deleted:")
                for user in unverified_users[:20]:  # Show first 20
                    self.stdout.write(f"  - {user.username} ({user.email}) - Created: {user.date_joined.date()}")
                if count > 20:
                    self.stdout.write(f"  ... and {count - 20} more")
        else:
            deleted_count = 0
            for user in unverified_users:
                self.stdout.write(f"Deleting user: {user.username} ({user.email})")
                user.delete()
                deleted_count += 1

            self.stdout.write(
                self.style.SUCCESS(f"Successfully deleted {deleted_count} unverified/inactive users")
            )
