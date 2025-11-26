# Generated migration to enforce email uniqueness

from django.db import migrations, models


def remove_duplicate_emails(apps, schema_editor):
    """
    Remove duplicate email addresses, keeping the user with the lowest ID (oldest account).
    Also normalizes all emails to lowercase for case-insensitive uniqueness.
    """
    User = apps.get_model("auth", "User")
    db_alias = schema_editor.connection.alias

    # First, normalize all emails to lowercase
    print("Normalizing all email addresses to lowercase...")
    users = User.objects.using(db_alias).all()
    for user in users:
        if user.email:
            normalized_email = user.email.lower()
            if user.email != normalized_email:
                user.email = normalized_email
                user.save(update_fields=["email"])

    # Handle NULL or empty emails by setting them to unique placeholder values
    print("Handling NULL or empty email addresses...")
    empty_email_users = User.objects.using(db_alias).filter(models.Q(email__isnull=True) | models.Q(email=""))
    empty_count = empty_email_users.count()
    for user in empty_email_users:
        user.email = f"user_{user.id}@placeholder.local"
        user.save(update_fields=["email"])
    print(f"Updated {empty_count} users with empty/NULL emails")

    # Find and remove duplicate emails
    print("Finding duplicate email addresses...")
    from django.db.models import Count

    duplicates = (
        User.objects.using(db_alias)
        .values("email")
        .annotate(email_count=Count("id"))
        .filter(email_count__gt=1)
        .order_by()
    )

    total_deleted = 0
    for duplicate in duplicates:
        email = duplicate["email"]
        print(f"Processing duplicates for email: {email}")

        # Get all users with this email, ordered by ID (oldest first)
        users_with_email = User.objects.using(db_alias).filter(email=email).order_by("id")

        # Keep the first user (oldest account) and delete the rest
        first_user = users_with_email.first()
        deleted_count = users_with_email.exclude(id=first_user.id).delete()[0]

        print(f"  Kept user {first_user.id} (username: {first_user.username}), deleted {deleted_count} duplicate(s)")
        total_deleted += deleted_count

    if total_deleted > 0:
        print(f"Total duplicate accounts removed: {total_deleted}")
    else:
        print("No duplicate email addresses found.")


def reverse_migration(apps, schema_editor):
    """
    Reverse operation - no-op since we cannot restore deleted users.
    The constraint removal is handled by the constraint operation itself.
    """
    print("Note: Deleted duplicate users cannot be restored.")


def add_email_constraint(apps, schema_editor):
    """
    Add unique constraint on email field in a database-agnostic way.
    """
    # Get the database vendor (postgresql, mysql, sqlite, etc.)
    vendor = schema_editor.connection.vendor

    if vendor == "postgresql":
        schema_editor.execute("ALTER TABLE auth_user ADD CONSTRAINT auth_user_email_unique UNIQUE (email);")
    elif vendor == "mysql":
        schema_editor.execute("ALTER TABLE auth_user ADD UNIQUE INDEX auth_user_email_unique (email);")
    elif vendor == "sqlite":
        # SQLite doesn't support adding constraints to existing tables easily
        # The constraint was already enforced by the data migration
        # and will be enforced at the application level
        print("SQLite detected: Unique constraint will be enforced at the application level")
    else:
        # For other databases, attempt standard SQL
        schema_editor.execute("ALTER TABLE auth_user ADD CONSTRAINT auth_user_email_unique UNIQUE (email);")


def remove_email_constraint(apps, schema_editor):
    """
    Remove unique constraint on email field in a database-agnostic way.
    """
    vendor = schema_editor.connection.vendor

    if vendor == "postgresql":
        schema_editor.execute("ALTER TABLE auth_user DROP CONSTRAINT IF EXISTS auth_user_email_unique;")
    elif vendor == "mysql":
        schema_editor.execute("ALTER TABLE auth_user DROP INDEX IF EXISTS auth_user_email_unique;")
    elif vendor == "sqlite":
        # SQLite doesn't support dropping constraints easily
        print("SQLite detected: No constraint to remove")
    else:
        # For other databases, attempt standard SQL
        try:
            schema_editor.execute("ALTER TABLE auth_user DROP CONSTRAINT auth_user_email_unique;")
        except Exception:
            pass  # Constraint may not exist


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
