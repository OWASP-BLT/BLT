# Generated migration to make email field unique
import logging

from django.db import migrations
from django.db.models import Count

logger = logging.getLogger(__name__)


def remove_duplicate_users(apps, schema_editor):
    """
    Remove users with duplicate non-empty emails.
    Keeps the user with the lowest ID (first created) and deletes the rest.
    Empty emails are preserved since the partial unique index allows them.
    """
    User = apps.get_model("auth", "User")
    db_alias = schema_editor.connection.alias

    # Find all duplicate non-empty emails
    duplicate_emails = (
        User.objects.using(db_alias)
        .exclude(email="")
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
        duplicate_users = users_with_email[1:]

        for user in duplicate_users:
            logger.info(
                f"Deleting duplicate user '{user.username}' (ID: {user.id}, email: '{email}'). "
                f"Keeping user '{kept_user.username}' (ID: {kept_user.id})"
            )
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
    logger.warning("Reversing migration 0259_make_email_unique: " "Deleted users cannot be restored.")


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0258_add_slackchannel_model"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        # Step 1: Delete duplicate users (keep first user)
        migrations.RunPython(
            remove_duplicate_users,
            reverse_code=reverse_migration,
        ),
        # Step 2: Add partial unique index that allows multiple empty emails
        migrations.RunSQL(
            sql="""
                CREATE UNIQUE INDEX IF NOT EXISTS auth_user_email_unique 
                ON auth_user (email) 
                WHERE email != '';
            """,
            reverse_sql="DROP INDEX IF EXISTS auth_user_email_unique;",
        ),
    ]
