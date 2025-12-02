"""
Management command to analyze duplicate emails before running the migration.

Usage:
    python manage.py analyze_duplicate_emails
    python manage.py analyze_duplicate_emails --detailed
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Count


class Command(BaseCommand):
    help = "Analyze duplicate email addresses before running migration 0259"

    def add_arguments(self, parser):
        parser.add_argument(
            "--detailed",
            action="store_true",
            help="Show detailed information about each duplicate",
        )

    def handle(self, *args, **options):
        detailed = options["detailed"]

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("DUPLICATE EMAIL ANALYSIS")
        self.stdout.write("=" * 80 + "\n")

        # Find duplicate non-empty, non-null emails (matching migration logic)
        duplicate_emails = (
            User.objects.exclude(email="")
            .exclude(email__isnull=True)
            .values("email")
            .annotate(email_count=Count("id"))
            .filter(email_count__gt=1)
            .order_by("-email_count")
        )

        # Check for empty string emails
        empty_email_count = User.objects.filter(email="").count()

        # Check for NULL emails
        null_email_count = User.objects.filter(email__isnull=True).count()

        if not duplicate_emails and empty_email_count <= 1 and null_email_count <= 1:
            self.stdout.write(self.style.SUCCESS("✓ No duplicate emails found!"))
            self.stdout.write("Migration 0259 can be run safely.\n")
            return

        total_to_delete = sum(d["email_count"] - 1 for d in duplicate_emails)

        self.stdout.write(
            self.style.WARNING(
                f"Found {len(duplicate_emails)} email(s) with duplicates\n"
                f"Total users to be DELETED: {total_to_delete}\n"
            )
        )

        for dup in duplicate_emails:
            email = dup["email"]
            count = dup["email_count"]

            self.stdout.write(f"\nEmail: {email}")
            self.stdout.write(f"  Total users: {count}")
            self.stdout.write(f"  Users to DELETE: {count - 1}")

            if detailed:
                users = User.objects.filter(email=email).order_by("id")
                kept_user = users.first()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ KEEP: {kept_user.username} (ID: {kept_user.id}, joined: {kept_user.date_joined})"
                    )
                )

                for user in users[1:]:
                    self.stdout.write(
                        self.style.ERROR(f"  ✗ DELETE: {user.username} (ID: {user.id}, joined: {user.date_joined})")
                    )

        # Report on empty string emails
        if empty_email_count > 0:
            self.stdout.write("\n" + "-" * 80)
            self.stdout.write(self.style.WARNING("EMPTY STRING EMAILS"))
            self.stdout.write("-" * 80)
            self.stdout.write(f"\nUsers with empty email (''): {empty_email_count}")

            if empty_email_count > 1:
                self.stdout.write(self.style.SUCCESS("✓ The migration will NOT treat these as duplicates."))
                self.stdout.write("  Multiple users can have empty emails (this is valid).")

            if detailed and empty_email_count > 0:
                self.stdout.write("\nUsers with empty email:")
                empty_users = User.objects.filter(email="").order_by("id")[:10]
                for user in empty_users:
                    self.stdout.write(f"  - {user.username} (ID: {user.id}, joined: {user.date_joined})")
                if empty_email_count > 10:
                    self.stdout.write(f"  ... and {empty_email_count - 10} more")

        # Report on NULL emails
        if null_email_count > 0:
            self.stdout.write("\n" + "-" * 80)
            self.stdout.write(self.style.WARNING("NULL EMAILS"))
            self.stdout.write("-" * 80)
            self.stdout.write(f"\nUsers with NULL email: {null_email_count}")

            if null_email_count > 1:
                self.stdout.write(self.style.SUCCESS("✓ The migration will NOT treat these as duplicates."))
                self.stdout.write("  Multiple users can have NULL emails (this is valid).")

            if detailed and null_email_count > 0:
                self.stdout.write("\nUsers with NULL email:")
                null_users = User.objects.filter(email__isnull=True).order_by("id")[:10]
                for user in null_users:
                    self.stdout.write(f"  - {user.username} (ID: {user.id}, joined: {user.date_joined})")
                if null_email_count > 10:
                    self.stdout.write(f"  ... and {null_email_count - 10} more")

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 80)
        self.stdout.write(f"Non-empty emails with duplicates: {len(duplicate_emails)}")
        self.stdout.write(f"Users to be DELETED: {total_to_delete}")
        self.stdout.write(f"Users with empty email (''): {empty_email_count}")
        self.stdout.write(f"Users with NULL email: {null_email_count}")
        self.stdout.write("\n" + self.style.WARNING("Migration 0259 will:"))
        self.stdout.write("  1. Keep the first user (lowest ID) for each duplicate non-empty email")
        self.stdout.write("  2. DELETE all other users with that non-empty email")
        self.stdout.write("  3. NOT delete users with empty or NULL emails (multiple allowed)")
        self.stdout.write("  4. Add a unique index on the email field")
        self.stdout.write("\n" + self.style.ERROR("⚠ DELETED USERS CANNOT BE RECOVERED!"))
        self.stdout.write("=" * 80 + "\n")
