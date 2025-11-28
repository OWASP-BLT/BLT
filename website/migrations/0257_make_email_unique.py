# Generated migration to make email field unique
from django.db import migrations
from django.db.models import Count


def remove_duplicate_emails(apps, schema_editor):
    """
    Remove users with duplicate emails, keeping only the first user (lowest ID).
    Handles both non-empty and empty email duplicates.
    """
    User = apps.get_model("auth", "User")
    db_alias = schema_editor.connection.alias

    # Find all duplicate emails (including empty emails)
    duplicate_emails = (
        User.objects.using(db_alias)
        .values("email")
        .annotate(email_count=Count("id"))
        .filter(email_count__gt=1)
        .values_list("email", flat=True)
    )

    deleted_count = 0
    for email in duplicate_emails:
        # Get all users with this email, ordered by ID
        users_with_email = User.objects.using(db_alias).filter(email=email).order_by("id")

        # Keep the first user (lowest ID), delete the rest
        users_to_delete = list(users_with_email[1:])

        for user in users_to_delete:
            email_display = f"'{user.email}'" if user.email else "(empty)"
            print(f"Deleting duplicate user: {user.username} (ID: {user.id}, Email: {email_display})")
            user.delete()
            deleted_count += 1

    if deleted_count > 0:
        print(f"Total duplicate users deleted: {deleted_count}")
    else:
        print("No duplicate emails found.")


def verify_no_duplicates(apps, schema_editor):
    """
    Pre-check to ensure no duplicate emails exist before applying constraint.
    This prevents partial migration state if constraint application fails.
    """
    User = apps.get_model("auth", "User")
    db_alias = schema_editor.connection.alias

    # Check for any remaining duplicates (including empty emails)
    duplicate_count = (
        User.objects.using(db_alias).values("email").annotate(email_count=Count("id")).filter(email_count__gt=1).count()
    )

    if duplicate_count > 0:
        raise Exception(
            f"Migration aborted: {duplicate_count} duplicate email(s) still exist. "
            "This should not happen. Please investigate and run remove_duplicate_emails again."
        )


def reverse_migration(apps, schema_editor):
    """
    Reverse migration - cannot restore deleted users, so this is a no-op.
    """
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0256_inviteorganization"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        # Step 1: Remove duplicate emails (including empty ones)
        migrations.RunPython(
            remove_duplicate_emails,
            reverse_code=reverse_migration,
        ),
        # Step 2: Verify no duplicates remain before applying constraint
        migrations.RunPython(
            verify_no_duplicates,
            reverse_code=migrations.RunPython.noop,
        ),
        # Step 3: Add partial unique index that allows multiple empty emails
        # This is PostgreSQL-specific but safe for the current setup
        migrations.RunSQL(
            sql="""
                CREATE UNIQUE INDEX auth_user_email_unique 
                ON auth_user (email) 
                WHERE email != '';
            """,
            reverse_sql="DROP INDEX IF EXISTS auth_user_email_unique;",
        ),
    ]
