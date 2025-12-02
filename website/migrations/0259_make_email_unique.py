# Generated migration to make email field unique
import logging

from django.db import migrations
from django.db.models import Count

logger = logging.getLogger(__name__)


def remove_duplicate_users(apps, schema_editor):
    """
    Remove users with duplicate emails.
    Keeps the user with the lowest ID (first created) and deletes the rest.

    Only non-empty emails are checked for duplicates. Multiple users can have
    empty or NULL emails (which is valid per Django's User model where email
    has blank=True).

    Note: This function deletes users one-by-one rather than using bulk_delete()
    to ensure database-level CASCADE behavior and maintain referential integrity.
    Historical models retrieved via apps.get_model() do not have project signal
    handlers attached, so Django signals will NOT be fired during this migration.
    """
    User = apps.get_model("auth", "User")
    db_alias = schema_editor.connection.alias

    # Find all duplicate emails
    # IMPORTANT: Exclude empty strings and NULL values to avoid treating
    # multiple users with empty/NULL emails as duplicates
    duplicate_emails = (
        User.objects.using(db_alias)
        .exclude(email="")
        .exclude(email__isnull=True)
        .values("email")
        .annotate(email_count=Count("id"))
        .filter(email_count__gt=1)
        .values_list("email", flat=True)
    )

    total_deleted = 0
    for email in duplicate_emails:
        # Get all users with this email, ordered by ID
        users_with_email = User.objects.using(db_alias).filter(email=email).order_by("id")

        # Keep the first user (lowest ID), delete the rest
        kept_user = users_with_email.first()

        # Edge case: if no users found (shouldn't happen, but be safe)
        if not kept_user:
            logger.warning(f"No users found for email '{email}', skipping")
            continue

        # Convert QuerySet slice to list to avoid issues with deleting while iterating
        duplicate_users = list(users_with_email[1:])

        for user in duplicate_users:
            logger.info(
                f"Deleting duplicate user '{user.username}' (ID: {user.id}, email: '{email}'). "
                f"Keeping user '{kept_user.username}' (ID: {kept_user.id})"
            )
            # Delete one-by-one to ensure database-level CASCADE behavior
            # This is intentionally not using bulk_delete() for data integrity
            # Use db_alias to ensure deletion happens on the correct database in multi-DB setups
            user.delete(using=db_alias)
            total_deleted += 1

    if total_deleted > 0:
        logger.info(f"Successfully deleted {total_deleted} duplicate user(s)")
    else:
        logger.info("No duplicate users found")


def reverse_migration(apps, schema_editor):
    """
    Reverse migration - cannot restore deleted users.

    WARNING: Users deleted by this migration cannot be recovered.
    """
    logger.warning("Reversing migration 0259_make_email_unique: Deleted users cannot be restored.")


def get_create_index_sql(apps, schema_editor):
    """
    Returns appropriate SQL for creating unique index based on database vendor.

    Creates a partial unique constraint on non-empty emails. Multiple users can
    have empty or NULL emails (which is valid per Django's User model), but each
    non-empty email must be unique.

    This function is called at migration execution time (not import time) to ensure
    the correct database connection is used in multi-database setups.
    """
    vendor = schema_editor.connection.vendor

    if vendor == "postgresql":
        # PostgreSQL - partial unique constraint excluding empty strings
        return """
            DO $$$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = 'auth_user_email_unique'
                ) THEN
                    CREATE UNIQUE INDEX auth_user_email_unique 
                    ON auth_user (email) WHERE email != '';
                END IF;
            END $$;
        """
    elif vendor == "sqlite":
        # SQLite - partial unique constraint excluding empty strings
        return """
            CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email_unique 
            ON auth_user (email) WHERE email != '';
        """
    elif vendor == "mysql":
        # MySQL doesn't support partial indexes with WHERE clause
        # We create a full unique index, but the application must handle empty emails
        # Note: This means on MySQL, only one user can have an empty email
        return """
            CREATE UNIQUE INDEX auth_user_email_unique 
            ON auth_user (email(255));
        """
    else:
        # Fallback - attempt partial unique constraint
        return """
            CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email_unique 
            ON auth_user (email) WHERE email != '';
        """


def get_drop_index_sql(apps, schema_editor):
    """
    Returns appropriate SQL for dropping the unique index.

    Handles PostgreSQL, SQLite, and MySQL properly.
    Returns no-op for other databases.

    This function is called at migration execution time (not import time) to ensure
    the correct database connection is used in multi-database setups.
    """
    vendor = schema_editor.connection.vendor

    if vendor == "postgresql":
        return "DROP INDEX IF EXISTS auth_user_email_unique;"
    elif vendor == "sqlite":
        return "DROP INDEX IF EXISTS auth_user_email_unique;"
    elif vendor == "mysql":
        return "DROP INDEX auth_user_email_unique ON auth_user;"
    else:
        return "SELECT 1;"  # No-op SQL


class Migration(migrations.Migration):
    # Atomic is True by default, ensuring all operations succeed or rollback together
    # This protects against partial deletions if something fails
    atomic = True

    dependencies = [
        ("website", "0258_add_slackchannel_model"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        # Step 1: Delete duplicate users (keep first user)
        # This runs in a transaction, so if it fails, no changes are committed
        # This step runs on ALL databases (deduplication is database-agnostic)
        migrations.RunPython(
            remove_duplicate_users,
            reverse_code=reverse_migration,
        ),
        # Step 2: Add unique constraint on non-empty emails
        # Partial unique constraint allows multiple users with empty emails (valid per Django's User model)
        # but enforces uniqueness for non-empty emails
        # SQL is selected at migration execution time based on the active database connection,
        # ensuring correct behavior in multi-database setups
        migrations.RunSQL(
            sql=get_create_index_sql,
            reverse_sql=get_drop_index_sql,
        ),
    ]
