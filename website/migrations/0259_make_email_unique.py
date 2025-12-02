# Generated migration to make email field unique
import logging

from django.db import migrations
from django.db.models import Count

logger = logging.getLogger(__name__)


def remove_duplicate_users(apps, schema_editor):
    """
    Remove users with duplicate emails.
    Keeps the user with the lowest ID (first created) and deletes the rest.

    Email is required for all users (including OAuth), so this migration enforces
    that all users have unique, non-empty email addresses.

    Note: This function deletes users one-by-one rather than using bulk_delete()
    to ensure Django signals are fired and cascade deletions are handled properly.
    """
    User = apps.get_model("auth", "User")
    db_alias = schema_editor.connection.alias

    # Find all duplicate emails (including empty/NULL which shouldn't exist)
    # Email is required for all users, so we check all email values
    duplicate_emails = (
        User.objects.using(db_alias)
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
            # Delete one-by-one to ensure signals fire and cascades work properly
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

    Creates a full unique constraint on email since email is required for all users
    (including OAuth users). No empty or NULL emails are allowed.

    This function is called at migration execution time (not import time) to ensure
    the correct database connection is used in multi-database setups.
    """
    vendor = schema_editor.connection.vendor

    if vendor == "postgresql":
        # PostgreSQL - full unique constraint on email
        return """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = 'auth_user_email_unique'
                ) THEN
                    CREATE UNIQUE INDEX auth_user_email_unique 
                    ON auth_user (email);
                END IF;
            END $$;
        """
    elif vendor == "sqlite":
        # SQLite - full unique constraint on email
        return """
            CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email_unique 
            ON auth_user (email);
        """
    elif vendor == "mysql":
        # MySQL - full unique constraint on email
        return """
            CREATE UNIQUE INDEX auth_user_email_unique 
            ON auth_user (email(255));
        """
    else:
        # Fallback for other databases - full unique constraint
        return """
            CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email_unique 
            ON auth_user (email);
        """


def get_drop_index_sql(apps, schema_editor):
    """
    Returns appropriate SQL for dropping the unique index.

    Only attempts to drop the index on PostgreSQL and SQLite where it was created.
    Returns no-op for other databases.

    This function is called at migration execution time (not import time) to ensure
    the correct database connection is used in multi-database setups.
    """
    vendor = schema_editor.connection.vendor

    if vendor in ("postgresql", "sqlite"):
        return "DROP INDEX IF EXISTS auth_user_email_unique;"
    else:
        # No index was created, so no need to drop anything
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
        # Step 2: Add unique constraint on email (all databases)
        # Email is required for all users including OAuth, so full unique constraint is enforced
        # SQL is selected at migration execution time based on the active database connection,
        # ensuring correct behavior in multi-database setups
        migrations.RunSQL(
            sql=get_create_index_sql,
            reverse_sql=get_drop_index_sql,
        ),
    ]
