"""
Enhanced management command to analyze duplicate emails with safety checks.

Usage:
    python manage.py analyze_duplicate_emails
    python manage.py analyze_duplicate_emails --detailed
    python manage.py analyze_duplicate_emails --show-activity
    python manage.py analyze_duplicate_emails --export-csv
"""

import csv

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Count, Sum
from django.utils import timezone


class Command(BaseCommand):
    help = "Analyze duplicate email addresses with enhanced safety checks before running migration 0264"

    def add_arguments(self, parser):
        parser.add_argument(
            "--detailed",
            action="store_true",
            help="Show detailed information about each duplicate",
        )
        parser.add_argument(
            "--show-activity",
            action="store_true",
            help="Show activity metrics (issues, points, last login) for each user",
        )
        parser.add_argument(
            "--export-csv",
            type=str,
            help="Export analysis to CSV file (provide filename)",
        )
        parser.add_argument(
            "--high-activity-only",
            action="store_true",
            help="Only show high-activity users that would be flagged",
        )

    def handle(self, *args, **options):
        detailed = options["detailed"]
        show_activity = options["show_activity"]
        export_csv = options["export_csv"]
        high_activity_only = options["high_activity_only"]

        # Safety thresholds - users above these will be flagged for manual review
        HIGH_ACTIVITY_THRESHOLDS = {
            "issues_reported": 5,  # Users with 5+ issues reported
            "points_earned": 100,  # Users with 100+ points
            "recent_login_days": 30,  # Users who logged in within 30 days
        }

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("ENHANCED DUPLICATE EMAIL ANALYSIS WITH SAFETY CHECKS")
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.WARNING("⚠️  IMPORTANT: BACKUP YOUR DATABASE BEFORE RUNNING MIGRATION!"))
        self.stdout.write("⚠️  Migration 0264 will DELETE user accounts and all associated data!")
        self.stdout.write("=" * 80 + "\n")

        # Import models here to avoid circular imports
        from website.models import Issue, Points

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
        null_email_count = User.objects.filter(email__isnull=True).count()

        if not duplicate_emails and empty_email_count <= 1 and null_email_count <= 1:
            self.stdout.write(self.style.SUCCESS("✅ No duplicate emails found!"))
            self.stdout.write("Migration 0264 can be run safely.\n")
            return

        total_to_delete = sum(d["email_count"] - 1 for d in duplicate_emails)
        high_activity_users = []
        csv_data = []

        self.stdout.write(
            self.style.WARNING(
                f"Found {len(duplicate_emails)} email(s) with duplicates\n"
                f"Total users to be DELETED: {total_to_delete}\n"
            )
        )

        for dup in duplicate_emails:
            email = dup["email"]
            count = dup["email_count"]

            # Get all users with this email, ordered by ID (newest first - what migration keeps)
            users = User.objects.filter(email=email).order_by("-id")
            kept_user = users.first()
            users_to_delete = list(users[1:])

            if not high_activity_only:
                self.stdout.write(f"\n📧 Email: {email}")
                self.stdout.write(f"  Total users: {count}")
                self.stdout.write(f"  Users to DELETE: {count - 1}")

            # Analyze each user for activity
            for i, user in enumerate(users):
                # Get user activity metrics
                issue_count = Issue.objects.filter(user=user).count()
                points_data = Points.objects.filter(user=user).aggregate(
                    total_points=Sum("score"), total_entries=Count("id")
                )
                total_points = points_data["total_points"] or 0
                points_entries = points_data["total_entries"] or 0

                # Check recent login
                recent_login = False
                days_since_login = None
                if user.last_login:
                    days_since_login = (timezone.now() - user.last_login).days
                    recent_login = days_since_login <= HIGH_ACTIVITY_THRESHOLDS["recent_login_days"]

                # Determine if high activity
                is_high_activity = (
                    issue_count >= HIGH_ACTIVITY_THRESHOLDS["issues_reported"]
                    or total_points >= HIGH_ACTIVITY_THRESHOLDS["points_earned"]
                    or recent_login
                )

                activity_summary = (
                    f"Issues: {issue_count}, "
                    f"Points: {total_points} ({points_entries} entries), "
                    f"Last login: {user.last_login.strftime('%Y-%m-%d') if user.last_login else 'Never'}"
                )

                user_info = {
                    "email": email,
                    "username": user.username,
                    "user_id": user.id,
                    "date_joined": user.date_joined,
                    "last_login": user.last_login,
                    "issue_count": issue_count,
                    "total_points": total_points,
                    "points_entries": points_entries,
                    "days_since_login": days_since_login,
                    "is_high_activity": is_high_activity,
                    "will_be_kept": i == 0,  # First user (newest) will be kept
                    "activity_summary": activity_summary,
                }

                if is_high_activity and not user_info["will_be_kept"]:
                    high_activity_users.append(user_info)

                # Add to CSV data
                csv_data.append(user_info)

                if not high_activity_only:
                    if i == 0:  # User to keep
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  ✅ KEEP: {user.username} (ID: {user.id}, joined: {user.date_joined.strftime('%Y-%m-%d')})"
                            )
                        )
                    else:  # User to delete
                        if is_high_activity:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"  🚨 DELETE (HIGH ACTIVITY): {user.username} (ID: {user.id}, joined: {user.date_joined.strftime('%Y-%m-%d')})"
                                )
                            )
                        else:
                            self.stdout.write(
                                self.style.ERROR(
                                    f"  ❌ DELETE: {user.username} (ID: {user.id}, joined: {user.date_joined.strftime('%Y-%m-%d')})"
                                )
                            )

                    if detailed or show_activity:
                        self.stdout.write(f"     📊 Activity: {activity_summary}")

        # Show high activity users summary
        if high_activity_users:
            self.stdout.write("\n" + "🚨" * 40)
            self.stdout.write(self.style.ERROR("HIGH ACTIVITY USERS DETECTED!"))
            self.stdout.write("🚨" * 40)
            self.stdout.write(
                self.style.ERROR(
                    f"Found {len(high_activity_users)} high-activity users that would be DELETED by migration!"
                )
            )
            self.stdout.write("These users should be manually reviewed:\n")

            for user_info in high_activity_users:
                self.stdout.write(f"📧 Email: {user_info['email']}")
                self.stdout.write(
                    self.style.ERROR(
                        f"  🚨 {user_info['username']} (ID: {user_info['user_id']}) - {user_info['activity_summary']}"
                    )
                )

            self.stdout.write("\n" + self.style.ERROR("RECOMMENDED ACTIONS:"))
            self.stdout.write("1. 📧 Contact these users to update their email addresses")
            self.stdout.write("2. 🔄 Manually merge their data if appropriate")
            self.stdout.write("3. ⚠️  Consider which account should be kept (newest vs most active)")
            self.stdout.write("4. 🔄 Re-run migration after manual cleanup")
            self.stdout.write("\n" + self.style.ERROR("⚠️  MIGRATION WILL BE BLOCKED until these are resolved!"))
            self.stdout.write("🚨" * 40)

        # Report on empty/null emails
        if empty_email_count > 0 or null_email_count > 0:
            self.stdout.write("\n" + "-" * 80)
            self.stdout.write("EMPTY/NULL EMAILS (NOT AFFECTED BY MIGRATION)")
            self.stdout.write("-" * 80)
            if empty_email_count > 0:
                self.stdout.write(f"Users with empty email (''): {empty_email_count}")
            if null_email_count > 0:
                self.stdout.write(f"Users with NULL email: {null_email_count}")
            self.stdout.write("✅ Multiple users can have empty/NULL emails (this is valid)")

        # Export to CSV if requested
        if export_csv:
            self.export_to_csv(csv_data, export_csv)

        # Final summary
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 80)
        self.stdout.write(f"Non-empty emails with duplicates: {len(duplicate_emails)}")
        self.stdout.write(f"Users to be DELETED: {total_to_delete}")
        self.stdout.write(f"High-activity users at risk: {len(high_activity_users)}")
        self.stdout.write(f"Users with empty email (''): {empty_email_count}")
        self.stdout.write(f"Users with NULL email: {null_email_count}")

        self.stdout.write("\n" + self.style.WARNING("Migration 0264 will:"))
        self.stdout.write("  1. Keep the NEWEST user (highest ID) for each duplicate email")
        self.stdout.write("  2. DELETE all OLDER users with that email")
        self.stdout.write("  3. HALT if high-activity users would be deleted")
        self.stdout.write("  4. NOT delete users with empty or NULL emails")
        self.stdout.write("  5. Add a unique index on the email field")

        if high_activity_users:
            self.stdout.write("\n" + self.style.ERROR("🚨 MIGRATION WILL BE BLOCKED - Manual review required!"))
        else:
            self.stdout.write("\n" + self.style.SUCCESS("✅ Migration can proceed safely"))

        self.stdout.write("\n" + self.style.ERROR("⚠️  BACKUP YOUR DATABASE BEFORE RUNNING MIGRATION!"))
        self.stdout.write("=" * 80 + "\n")

    def export_to_csv(self, csv_data, filename):
        """Export analysis data to CSV file"""
        try:
            with open(filename, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = [
                    "email",
                    "username",
                    "user_id",
                    "date_joined",
                    "last_login",
                    "issue_count",
                    "total_points",
                    "points_entries",
                    "days_since_login",
                    "is_high_activity",
                    "will_be_kept",
                    "activity_summary",
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()

                for row in csv_data:
                    # Format dates for CSV
                    row_copy = row.copy()
                    if row_copy["date_joined"]:
                        row_copy["date_joined"] = row_copy["date_joined"].strftime("%Y-%m-%d %H:%M:%S")
                    if row_copy["last_login"]:
                        row_copy["last_login"] = row_copy["last_login"].strftime("%Y-%m-%d %H:%M:%S")
                    writer.writerow(row_copy)

            self.stdout.write(self.style.SUCCESS(f"✅ Analysis exported to: {filename}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Failed to export CSV: {e}"))
