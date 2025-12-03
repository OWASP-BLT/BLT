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


def create_email_unique_index(apps, schema_editor):
    """
    Create unique index on email field based on database vendor.

    Creates a partial unique constraint on non-empty emails. Multiple users can
    have empty or NULL emails (which is valid per Django's User model), but each
    non-empty email must be unique.

    Note: On MySQL, empty string emails are converted to NULL before creating
    the index, since MySQL doesn't support partial indexes but allows multiple
    NULLs in unique indexes.
    """
    vendor = schema_editor.connection.vendor

    if vendor == "postgresql":
        # PostgreSQL - partial unique constraint excluding empty strings and NULLs
        sql = """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_indexes 
                    WHERE indexname = 'auth_user_email_unique'
                ) THEN
                    CREATE UNIQUE INDEX auth_user_email_unique 
                    ON auth_user (email) WHERE email IS NOT NULL AND email != '';
                END IF;
            END $$;
        """
    elif vendor == "sqlite":
        # SQLite - partial unique constraint excluding empty strings and NULLs
        sql = """
            CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email_unique 
            ON auth_user (email) WHERE email IS NOT NULL AND email != '';
        """
    elif vendor == "mysql":
        # MySQL doesn't support partial indexes with WHERE clause
        # Convert empty emails to NULL first (MySQL allows multiple NULLs in unique indexes)
        # WARNING: This makes the migration irreversible on MySQL because we cannot
        # distinguish original NULLs from converted empty strings during rollback
        schema_editor.execute("UPDATE auth_user SET email = NULL WHERE email = '';")
        sql = """
            CREATE UNIQUE INDEX auth_user_email_unique 
            ON auth_user (email(254));
        """
    else:
        # Fallback - attempt partial unique constraint
        sql = """
            CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email_unique 
            ON auth_user (email) WHERE email IS NOT NULL AND email != '';
        """

    schema_editor.execute(sql)


def drop_email_unique_index(apps, schema_editor):
    """
    Drop the unique index on email field.

    Handles PostgreSQL, SQLite, and MySQL properly.
    Returns no-op for other databases.
    """
    vendor = schema_editor.connection.vendor

    if vendor == "postgresql":
        sql = "DROP INDEX IF EXISTS auth_user_email_unique;"
    elif vendor == "sqlite":
        sql = "DROP INDEX IF EXISTS auth_user_email_unique;"
    elif vendor == "mysql":
        # MySQL migration is not reversible because we cannot distinguish between:
        # 1. Original NULL emails (legitimate)
        # 2. Empty strings converted to NULL by the forward migration
        # Attempting to reverse would cause data loss. Rollback must be done manually.
        from django.db.migrations.exceptions import IrreversibleError

        raise IrreversibleError(
            "Cannot reverse migration on MySQL: empty string emails were converted to NULL "
            "and cannot be safely restored. Manual rollback required."
        )
    else:
        sql = None

    if sql:
        schema_editor.execute(sql)


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
        # SQL is generated and executed at runtime based on the active database connection,
        # ensuring correct behavior in multi-database setups
        migrations.RunPython(
            code=create_email_unique_index,
            reverse_code=drop_email_unique_index,
        ),
    ]
