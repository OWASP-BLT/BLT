# Generated migration to make email field unique
from django.db import migrations
from django.db.models import Count


def remove_duplicate_emails(apps, schema_editor):
    """
    Remove users with duplicate emails, keeping only the first user (lowest ID).
    """
    User = apps.get_model("auth", "User")
    db_alias = schema_editor.connection.alias

    # Find all duplicate emails (excluding empty emails)
    duplicate_emails = (
        User.objects.using(db_alias)
        .exclude(email="")
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
            print(f"Deleting duplicate user: {user.username} (ID: {user.id}, Email: {user.email})")
            user.delete()
            deleted_count += 1

    if deleted_count > 0:
        print(f"Total duplicate users deleted: {deleted_count}")
    else:
        print("No duplicate emails found.")


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

    # Use atomic=False to allow the operations to run in separate transactions
    atomic = False

    operations = [
        # First, remove duplicate emails
        migrations.RunPython(
            remove_duplicate_emails,
            reverse_code=reverse_migration,
        ),
        # Then, add unique constraint to email field using RunSQL
        migrations.RunSQL(
            sql="ALTER TABLE auth_user ADD CONSTRAINT auth_user_email_unique UNIQUE (email);",
            reverse_sql="ALTER TABLE auth_user DROP CONSTRAINT IF EXISTS auth_user_email_unique;",
        ),
    ]
