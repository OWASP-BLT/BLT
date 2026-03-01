# Safe migration to make email field unique with enhanced safety checks
"""
Safe migration to make email field unique with enhanced safety checks.

RUNTIME EXPECTATIONS:
====================
- Small datasets (<1000 users): ~5-30 seconds
- Medium datasets (1000-10000 users): 1-5 minutes  
- Large datasets (>10000 users): 5-30 minutes

DATABASE LOCKING:
=================
PostgreSQL:
  - Uses standard CREATE UNIQUE INDEX which acquires AccessExclusiveLock
  - Blocks all reads/writes to auth_user table during index creation
  - For zero-downtime, use CREATE UNIQUE INDEX CONCURRENTLY (see below)
  - Lock duration: ~1-10 seconds per 10k rows

MySQL:
  - CREATE INDEX acquires metadata locks
  - Blocks writes but allows reads (table-level lock)
  - Lock duration: ~5-30 seconds per 10k rows
  - InnoDB uses online DDL by default (less blocking in MySQL 5.6+)

SQLite:
  - Database-level locking (blocks all operations)
  - Lock duration: Typically <5 seconds for reasonable datasets
  - Recommend running during maintenance window

DOWNTIME MITIGATION:
====================
For production PostgreSQL with zero-downtime requirements, manually run:

    CREATE UNIQUE INDEX CONCURRENTLY auth_user_email_unique_safe 
    ON auth_user (email) WHERE email IS NOT NULL AND email != '';
    
Then use --fake to skip the index creation step:
  python manage.py migrate website 0264 --fake

MYSQL LIMITATION:
=================
MySQL does not support partial unique indexes with WHERE clauses.
This migration will NOT create a unique constraint on MySQL databases.
Multiple users can still have the same non-empty email address on MySQL.
For full email uniqueness support, use PostgreSQL or SQLite.

ALWAYS BACKUP YOUR DATABASE BEFORE RUNNING THIS MIGRATION!
"""
import csv
import logging
from datetime import datetime

from django.db import migrations
from django.db.models import Count, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

logger = logging.getLogger(__name__)


def remove_duplicate_users_safely(apps, schema_editor):
    """
    Safely remove users with duplicate emails with enhanced safety checks.

    Safety features:
    - Activity threshold checks to prevent deletion of high-activity users
    - Backup recommendations in migration docs
    - Detailed logging of what will be deleted
    - Preserves newest account (highest ID) instead of oldest (more likely to be active)

    Only non-empty emails are checked for duplicates. Multiple users can have
    empty or NULL emails (which is valid per Django's User model where email
    has blank=True).
    """
    User = apps.get_model("auth", "User")
    Issue = apps.get_model("website", "Issue")
    Points = apps.get_model("website", "Points")
    db_alias = schema_editor.connection.alias

    # Safety thresholds - users above these will be flagged for manual review
    HIGH_ACTIVITY_THRESHOLDS = {
        "issues_reported": 5,  # Users with 5+ issues reported
        "points_earned": 100,  # Users with 100+ points
        "recent_login_days": 30,  # Users who logged in within 30 days
    }

    logger.info("=" * 80)
    logger.info("STARTING SAFE DUPLICATE EMAIL REMOVAL")
    logger.info("=" * 80)
    logger.info("IMPORTANT: Ensure you have backed up your database before running this migration!")
    logger.info("This migration will DELETE user accounts and all associated data!")
    logger.info("=" * 80)

    duplicate_emails = list(
        User.objects.using(db_alias)
        .exclude(email="")
        .exclude(email__isnull=True)
        .values("email")
        .annotate(email_count=Count("id"))
        .filter(email_count__gt=1)
        .values_list("email", flat=True)
    )

    if not duplicate_emails:
        logger.info("No duplicate emails found. Migration completed safely.")
        return

    users_with_metrics = (
        User.objects.using(db_alias)
        .filter(email__in=duplicate_emails)
        .annotate(
            issue_count=Coalesce(
                Subquery(
                    Issue.objects.filter(user=OuterRef("pk"))
                    .values("user")
                    .annotate(count=Count("pk"))
                    .values("count")[:1]
                ),
                0,
            ),
            total_points=Coalesce(
                Subquery(
                    Points.objects.filter(user=OuterRef("pk"))
                    .values("user")
                    .annotate(total=Sum("score"))
                    .values("total")[:1]
                ),
                0,
            ),
        )
        .order_by("email", "-id")
    )

    # Group users by email for processing
    users_by_email = {}
    for user in users_with_metrics:
        if user.email not in users_by_email:
            users_by_email[user.email] = []
        users_by_email[user.email].append(user)

    total_users_to_delete = 0
    high_activity_users = []

    for email in duplicate_emails:
        users_with_email = users_by_email.get(email, [])

        if not users_with_email:
            logger.warning(f"No users found for email '{email}', skipping")
            continue

        kept_user = users_with_email[0]
        users_to_delete = users_with_email[1:]

        logger.info(f"\nProcessing email: {email}")
        logger.info(f"   Total users: {len(users_with_email)}")
        logger.info(f"   KEEPING: {kept_user.username} (ID: {kept_user.id}, joined: {kept_user.date_joined})")

        for user in users_to_delete:
            issue_count = user.issue_count or 0
            total_points = user.total_points or 0

            # Check recent login (last_login can be None)
            recent_login = False
            if user.last_login:
                days_since_login = (timezone.now() - user.last_login).days
                recent_login = days_since_login <= HIGH_ACTIVITY_THRESHOLDS["recent_login_days"]

            # Check if user exceeds activity thresholds
            is_high_activity = (
                issue_count >= HIGH_ACTIVITY_THRESHOLDS["issues_reported"]
                or total_points >= HIGH_ACTIVITY_THRESHOLDS["points_earned"]
                or recent_login
            )

            activity_info = (
                f"Issues: {issue_count}, " f"Points: {total_points}, " f"Last login: {user.last_login or 'Never'}"
            )

            if is_high_activity:
                logger.error(f"   HIGH ACTIVITY USER FLAGGED: {user.username} (ID: {user.id}) - {activity_info}")
                high_activity_users.append(
                    {"user": user, "email": email, "activity": activity_info, "kept_user": kept_user}
                )
            else:
                logger.info(f"   Will delete: {user.username} (ID: {user.id}) - {activity_info}")
                total_users_to_delete += 1

    if high_activity_users:
        logger.error("\n" + "!" * 40)
        logger.error("HIGH ACTIVITY USERS DETECTED!")
        logger.error("!" * 40)
        logger.error(f"Found {len(high_activity_users)} high-activity users that would be deleted.")
        logger.error("These users should be manually reviewed before deletion:")
        logger.error("")

        for user_info in high_activity_users:
            user = user_info["user"]
            logger.error(f"Email: {user_info['email']}")
            logger.error(f"  HIGH ACTIVITY: {user.username} (ID: {user.id}) - {user_info['activity']}")
            logger.error(f"  Would keep: {user_info['kept_user'].username} (ID: {user_info['kept_user'].id})")
            logger.error("")

        logger.error("RECOMMENDED ACTIONS:")
        logger.error("1. Contact these users to update their email addresses")
        logger.error("2. Manually merge their data if appropriate")
        logger.error("3. Re-run migration after manual cleanup")
        logger.error("")
        logger.error("Migration ABORTED for safety. No users were deleted.")
        logger.error("!" * 40)

        # Raise exception to halt migration
        raise Exception(
            f"Migration halted: {len(high_activity_users)} high-activity users detected. "
            "Manual review required before proceeding."
        )

    logger.info(f"\nSafety check passed. {total_users_to_delete} low-activity users will be deleted.")

    deletion_csv = f"deleted_users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    actual_deleted = 0

    with open(deletion_csv, "w", newline="", encoding="utf-8") as csv_file:
        fieldnames = [
            "user_id",
            "username",
            "email",
            "date_joined",
            "last_login",
            "issue_count",
            "total_points",
            "kept_user_id",
            "kept_user_username",
            "deletion_timestamp",
        ]
        csv_writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        csv_writer.writeheader()

        for email in duplicate_emails:
            users_with_email = users_by_email.get(email, [])
            if not users_with_email:
                continue

            kept_user = users_with_email[0]
            users_to_delete = users_with_email[1:]

            for user in users_to_delete:
                issue_count = user.issue_count or 0
                total_points = user.total_points or 0

                recent_login = False
                if user.last_login:
                    days_since_login = (timezone.now() - user.last_login).days
                    recent_login = days_since_login <= HIGH_ACTIVITY_THRESHOLDS["recent_login_days"]

                if (
                    issue_count >= HIGH_ACTIVITY_THRESHOLDS["issues_reported"]
                    or total_points >= HIGH_ACTIVITY_THRESHOLDS["points_earned"]
                    or recent_login
                ):
                    logger.error(f"SAFETY VIOLATION: High activity user {user.username} detected during deletion!")
                    raise Exception(
                        f"Safety violation: User {user.username} has high activity and should not be deleted"
                    )

                try:
                    csv_writer.writerow(
                        {
                            "user_id": user.id,
                            "username": user.username,
                            "email": email,
                            "date_joined": user.date_joined,
                            "last_login": user.last_login,
                            "issue_count": issue_count,
                            "total_points": total_points,
                            "kept_user_id": kept_user.id,
                            "kept_user_username": kept_user.username,
                            "deletion_timestamp": datetime.now(),
                        }
                    )
                except Exception as csv_error:
                    logger.warning(f"Failed to write CSV record for user {user.username}: {csv_error}")

                logger.info(f"Deleting user: {user.username} (ID: {user.id}, email: '{email}')")
                logger.info(f"   Keeping: {kept_user.username} (ID: {kept_user.id})")

                user.delete(using=db_alias)
                actual_deleted += 1

    logger.info(f"Deletion records exported to: {deletion_csv}")

    logger.info(f"\nSuccessfully deleted {actual_deleted} duplicate users")
    logger.info("Email uniqueness migration completed safely")
    logger.info("=" * 80)


def reverse_migration(apps, schema_editor):
    """
    Reverse migration - cannot restore deleted users.
    """
    logger.warning("Reversing migration 0264_make_email_unique_safe")
    logger.warning("DELETED USERS CANNOT BE RESTORED!")
    logger.warning("This reverse operation only removes the unique constraint.")


def create_email_unique_index(apps, schema_editor):
    """
    Create unique index on email field based on database vendor.

    Creates a partial unique constraint on non-empty emails. Multiple users can
    have empty or NULL emails (which is valid per Django's User model), but each
    non-empty email must be unique.
    """
    vendor = schema_editor.connection.vendor

    if vendor == "postgresql":
        sql = """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = 'auth_user_email_unique_safe'
                ) THEN
                    CREATE UNIQUE INDEX auth_user_email_unique_safe 
                    ON auth_user (email) WHERE email IS NOT NULL AND email != '';
                END IF;
            END $$;
        """
    elif vendor == "sqlite":
        sql = """
            CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email_unique_safe 
            ON auth_user (email) WHERE email IS NOT NULL AND email != '';
        """
    elif vendor == "mysql":
        # MySQL doesn't support partial indexes with WHERE clause like PostgreSQL/SQLite
        # We need to handle empty emails differently for MySQL
        #
        # Option 1: Don't create unique constraint on MySQL (document this limitation)
        # Option 2: Create a custom unique constraint that handles empty emails
        #
        # For now, we'll skip the unique constraint on MySQL and document this
        # as a known limitation. This prevents the migration from failing.
        logger.warning(
            "MySQL detected: Unique email constraint not created due to MySQL limitations. "
            "Multiple users can still have the same non-empty email address on MySQL. "
            "Consider using PostgreSQL or SQLite for full email uniqueness support."
        )
        sql = None  # Skip index creation for MySQL
    else:
        sql = """
            CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email_unique_safe 
            ON auth_user (email) WHERE email IS NOT NULL AND email != '';
        """

    if sql:
        schema_editor.execute(sql)


def drop_email_unique_index(apps, schema_editor):
    """
    Drop the unique index on email field.
    """
    vendor = schema_editor.connection.vendor

    if vendor == "postgresql":
        sql = "DROP INDEX IF EXISTS auth_user_email_unique_safe;"
    elif vendor == "sqlite":
        sql = "DROP INDEX IF EXISTS auth_user_email_unique_safe;"
    elif vendor == "mysql":
        # MySQL: No unique constraint was created, so nothing to drop
        logger.info("MySQL detected: No unique email constraint to drop (none was created)")
        sql = None
    else:
        sql = None

    if sql:
        schema_editor.execute(sql)


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("website", "0270_githubcomment"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        # Step 1: Safely delete duplicate users with activity checks
        migrations.RunPython(
            remove_duplicate_users_safely,
            reverse_code=reverse_migration,
        ),
        # Step 2: Add unique constraint on non-empty emails
        migrations.RunPython(
            code=create_email_unique_index,
            reverse_code=drop_email_unique_index,
        ),
    ]
