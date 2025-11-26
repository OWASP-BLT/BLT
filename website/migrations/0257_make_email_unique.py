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
    for user in empty_email_users:
        user.email = f"user_{user.id}@placeholder.local"
        user.save(update_fields=["email"])
    print(f"Updated {empty_email_users.count()} users with empty/NULL emails")

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

        # Count duplicates before deletion
        duplicate_count = users_with_email.count() - 1

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


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0256_inviteorganization"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        # First, remove duplicates and normalize emails
        migrations.RunPython(remove_duplicate_emails, reverse_migration),
        # Then, add the unique constraint at the database level
        migrations.AddConstraint(
            model_name="user",
            constraint=models.UniqueConstraint(
                fields=["email"],
                name="auth_user_email_unique",
            ),
        ),
    ]
