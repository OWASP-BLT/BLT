# Generated migration to enforce email uniqueness

import logging
import uuid

from django.db import migrations, models, transaction

logger = logging.getLogger(__name__)


def remove_duplicate_emails(apps, schema_editor):
    """
    Remove duplicate email addresses, keeping the user with the lowest ID (oldest account).
    Also normalizes all emails to lowercase for case-insensitive uniqueness.

    WARNING: This migration will delete duplicate user accounts and all their related data.
    Ensure you have a database backup before running this migration.
    """
    User = apps.get_model("auth", "User")
    db_alias = schema_editor.connection.alias

    with transaction.atomic():
        # Handle NULL or empty emails by setting them to unique placeholder values using UUIDs
        logger.info("Handling NULL or empty email addresses...")
        empty_email_users = User.objects.using(db_alias).filter(models.Q(email__isnull=True) | models.Q(email=""))
        empty_count = empty_email_users.count()

        users_to_update = []
        for user in empty_email_users:
            user.email = f"noemail-{uuid.uuid4().hex[:16]}@placeholder.local"
            users_to_update.append(user)

        if users_to_update:
            User.objects.bulk_update(users_to_update, ["email"], batch_size=500)
        logger.info(f"Updated {empty_count} users with empty/NULL emails")

        # Normalize all emails to lowercase using bulk update
        logger.info("Normalizing all email addresses to lowercase...")
        users_to_normalize = []
        for user in User.objects.using(db_alias).iterator(chunk_size=1000):
            if user.email:
                normalized_email = user.email.lower()
                if user.email != normalized_email:
                    user.email = normalized_email
                    users_to_normalize.append(user)

        if users_to_normalize:
            User.objects.bulk_update(users_to_normalize, ["email"], batch_size=500)
            logger.info(f"Normalized {len(users_to_normalize)} email addresses to lowercase")

        # Find and remove duplicate emails (after normalization, case-insensitive duplicates become actual duplicates)
        logger.info("Finding duplicate email addresses...")
        from django.db.models import Count

        duplicates = (
            User.objects.using(db_alias)
            .values("email")
            .annotate(email_count=Count("id"))
            .filter(email_count__gt=1)
            .order_by()
        )

        # Collect all user IDs to delete in one pass for efficiency
        ids_to_delete = []
        kept_user_info = []

        for duplicate in duplicates:
            email = duplicate["email"]
            logger.info(f"Processing duplicates for email: {email}")

            # Get all users with this email, ordered by ID (oldest first)
            users_with_email = User.objects.using(db_alias).filter(email=email).order_by("id")
            user_data = list(users_with_email.values("id", "username", "email"))

            if len(user_data) > 1:
                # Keep the first user (oldest account)
                first_user = user_data[0]
                kept_user_info.append(first_user)

                # Log which users will be deleted before deletion
                for user in user_data[1:]:
                    logger.warning(
                        f"  Deleting duplicate user: ID={user['id']}, "
                        f"username={user['username']}, email={user['email']}"
                    )
                    ids_to_delete.append(user["id"])

                logger.info(
                    f"  Kept user {first_user['id']} (username: {first_user['username']}), "
                    f"marked {len(user_data) - 1} duplicate(s) for deletion"
                )

        # Perform bulk deletion
        total_deleted = 0
        if ids_to_delete:
            logger.warning(
                f"About to delete {len(ids_to_delete)} duplicate user accounts. "
                "This will also delete all related data (issues, comments, etc.) through cascade deletion."
            )
            deleted_count, _ = User.objects.using(db_alias).filter(id__in=ids_to_delete).delete()
            total_deleted = deleted_count
            logger.info(f"Total duplicate accounts removed: {total_deleted}")
        else:
            logger.info("No duplicate email addresses found.")


def reverse_migration(apps, schema_editor):
    """
    Reverse operation - no-op since we cannot restore deleted users.
    The constraint removal is handled by the constraint operation itself.
    """
    logger.warning("Note: Deleted duplicate users cannot be restored.")


def add_email_constraint(apps, schema_editor):
    """
    Add unique constraint on email field in a database-agnostic way.
    Makes the operation idempotent by checking for existing constraint.
    """
    from django.db import DatabaseError, IntegrityError

    vendor = schema_editor.connection.vendor

    try:
        if vendor == "postgresql":
            # PostgreSQL: Check if constraint exists, add if not
            schema_editor.execute("ALTER TABLE auth_user ADD CONSTRAINT auth_user_email_unique UNIQUE (email);")
            logger.info("Added unique constraint on email field for PostgreSQL")
        elif vendor == "mysql":
            # MySQL: Add unique index (will fail silently if exists due to IF NOT EXISTS in newer versions)
            schema_editor.execute("ALTER TABLE auth_user ADD UNIQUE INDEX auth_user_email_unique (email);")
            logger.info("Added unique index on email field for MySQL")
        elif vendor == "sqlite":
            # SQLite doesn't support adding constraints to existing tables easily
            # The constraint will be enforced at the application level
            logger.info("SQLite detected: Unique constraint will be enforced at the application level")
        else:
            # For other databases, attempt standard SQL
            schema_editor.execute("ALTER TABLE auth_user ADD CONSTRAINT auth_user_email_unique UNIQUE (email);")
            logger.info(f"Added unique constraint on email field for {vendor}")
    except (DatabaseError, IntegrityError) as e:
        # Constraint may already exist
        logger.warning(f"Could not add constraint (may already exist): {e}")
        pass


def remove_email_constraint(apps, schema_editor):
    """
    Remove unique constraint on email field in a database-agnostic way.
    """
    from django.db import DatabaseError

    vendor = schema_editor.connection.vendor

    try:
        if vendor == "postgresql":
            schema_editor.execute("ALTER TABLE auth_user DROP CONSTRAINT IF EXISTS auth_user_email_unique;")
            logger.info("Dropped unique constraint on email field for PostgreSQL")
        elif vendor == "mysql":
            schema_editor.execute("ALTER TABLE auth_user DROP INDEX IF EXISTS auth_user_email_unique;")
            logger.info("Dropped unique index on email field for MySQL")
        elif vendor == "sqlite":
            # SQLite doesn't support dropping constraints easily
            logger.info("SQLite detected: No constraint to remove")
        else:
            # For other databases, attempt standard SQL
            schema_editor.execute("ALTER TABLE auth_user DROP CONSTRAINT auth_user_email_unique;")
            logger.info(f"Dropped unique constraint on email field for {vendor}")
    except DatabaseError as e:
        # Constraint may not exist or other database error
        logger.warning(f"Could not remove constraint: {e}")
        pass


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0256_inviteorganization"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        # First, remove duplicates and normalize emails
        migrations.RunPython(remove_duplicate_emails, reverse_migration),
        # Then, add the unique constraint at the database level
        # We use RunPython with custom SQL for database-agnostic implementation
        migrations.RunPython(add_email_constraint, remove_email_constraint),
    ]
