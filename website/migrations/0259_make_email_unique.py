# Generated migration to make email field unique
import json
import logging
from datetime import datetime

from django.db import migrations
from django.db.models import Count
from django.db.models.deletion import Collector

logger = logging.getLogger(__name__)


def analyze_related_objects(user, using):
    """
    Use Django's Collector to enumerate all related objects for a user.
    Returns a dictionary of related objects grouped by model.
    """
    collector = Collector(using=using)
    collector.collect([user])

    related_objects = {}
    for model, instances in collector.data.items():
        model_name = f"{model._meta.app_label}.{model._meta.model_name}"
        related_objects[model_name] = [
            {
                "id": obj.pk,
                "repr": str(obj)[:100],  # Truncate long representations
            }
            for obj in instances
        ]

    return related_objects


def log_audit_entry(user, related_objects, action, reason):
    """
    Create an audit log entry for user deletion/archival.
    Logs using Django logger for production compatibility.
    """
    audit_entry = {
        "timestamp": datetime.now().isoformat(),
        "action": action,
        "reason": reason,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "date_joined": user.date_joined.isoformat() if hasattr(user, "date_joined") else None,
        },
        "related_objects": related_objects,
        "related_object_count": sum(len(objs) for objs in related_objects.values()),
    }

    logger.info("=" * 80)
    logger.info(f"AUDIT LOG - {action.upper()}")
    logger.info("=" * 80)
    logger.info(json.dumps(audit_entry, indent=2))
    logger.info("=" * 80)

    return audit_entry


def remove_duplicate_emails(apps, schema_editor):
    """
    Safely handle users with duplicate non-empty emails.

    Strategy:
    1. Identify duplicate emails (keeping user with lowest ID)
    2. For each duplicate user, use Collector to enumerate related objects
    3. Log all related objects in audit trail
    4. Anonymize user data instead of hard delete (soft-delete approach)
    5. Clear email to allow unique constraint

    This prevents cascade deletion and data loss while still allowing
    the unique constraint to be applied.

    WARNING: This migration uses soft-delete (anonymization). Users are NOT
    permanently deleted but are marked inactive with cleared emails. This
    preserves all related data and foreign key relationships. The reverse
    migration cannot restore the original user data.
    """
    User = apps.get_model("auth", "User")
    db_alias = schema_editor.connection.alias

    # Configuration: Set to True to perform actual operations, False for dry-run
    DRY_RUN = False

    # Find all duplicate non-empty emails (exclude empty emails)
    duplicate_emails = (
        User.objects.using(db_alias)
        .exclude(email="")
        .values("email")
        .annotate(email_count=Count("id"))
        .filter(email_count__gt=1)
        .values_list("email", flat=True)
    )

    processed_count = 0
    audit_logs = []

    if DRY_RUN:
        logger.warning("=" * 80)
        logger.warning("DRY RUN MODE - No changes will be made")
        logger.warning("=" * 80)

    for email in duplicate_emails:
        # Get all users with this email, ordered by ID
        users_with_email = User.objects.using(db_alias).filter(email=email).order_by("id")

        # Keep the first user (lowest ID), process the rest
        users_to_process = list(users_with_email[1:])

        for user in users_to_process:
            # Analyze all related objects before making changes
            related_objects = analyze_related_objects(user, db_alias)

            # Log the audit entry
            audit_log = log_audit_entry(
                user,
                related_objects,
                action="dry_run_anonymize" if DRY_RUN else "anonymize",
                reason=f"Duplicate email: {email}",
            )
            audit_logs.append(audit_log)

            if not DRY_RUN:
                # Soft-delete approach: Anonymize the user instead of deleting
                # This preserves all related objects and foreign key relationships
                user.email = ""  # Clear email to resolve duplicate
                user.username = f"deleted_user_{user.id}_{datetime.now().timestamp()}"
                user.is_active = False

                # Mark as archived if the field exists
                if hasattr(user, "is_deleted"):
                    user.is_deleted = True
                if hasattr(user, "archived"):
                    user.archived = True

                user.save()

                logger.info(f"✓ Anonymized user ID {user.id} (was: {email})")
            else:
                logger.info(f"[DRY RUN] Would anonymize user ID {user.id} (email: {email})")
                logger.info(
                    f"  - Related objects: {sum(len(objs) for objs in related_objects.values())} across {len(related_objects)} models"
                )

            processed_count += 1

    # Summary
    logger.info("=" * 80)
    logger.info("MIGRATION SUMMARY")
    logger.info("=" * 80)
    if DRY_RUN:
        logger.warning(f"DRY RUN: Would process {processed_count} duplicate users")
        logger.warning("Set DRY_RUN = False in the migration to apply changes")
    else:
        logger.info(f"Successfully processed {processed_count} duplicate users")
        logger.info("All users have been anonymized (soft-deleted) to preserve related data")

    if processed_count == 0:
        logger.info("No duplicate non-empty emails found.")

    logger.info("=" * 80)

    return audit_logs


def verify_no_duplicates(apps, schema_editor):
    """
    Pre-check to ensure no duplicate non-empty emails exist before applying constraint.
    This prevents partial migration state if constraint application fails.
    Empty emails are excluded from this check since the partial unique index allows them.
    """
    User = apps.get_model("auth", "User")
    db_alias = schema_editor.connection.alias

    # Check for any remaining non-empty duplicate emails (exclude empty emails)
    duplicate_count = (
        User.objects.using(db_alias)
        .exclude(email="")
        .values("email")
        .annotate(email_count=Count("id"))
        .filter(email_count__gt=1)
        .count()
    )

    if duplicate_count > 0:
        raise RuntimeError(
            f"Migration aborted: {duplicate_count} duplicate non-empty email(s) still exist. "
            "This should not happen. Please investigate and run remove_duplicate_emails again."
        )


def reverse_migration(apps, schema_editor):
    """
    Reverse migration - cannot restore anonymized users, so this is a no-op.

    WARNING: Users anonymized by this migration cannot be recovered. Their
    original usernames and emails have been permanently modified. While the
    user records still exist in the database (soft-delete), the original
    data cannot be restored through migration reversal.
    """
    logger.warning(
        "=" * 80 + "\n"
        "WARNING: Reversing migration 0259_make_email_unique\n"
        "Anonymized users CANNOT be restored to their original state.\n"
        "User records remain in database but original usernames/emails are lost.\n"
        "=" * 80
    )


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("website", "0258_add_slackchannel_model"),
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        # Step 1: Remove duplicate non-empty emails (empty emails are preserved)
        migrations.RunPython(
            remove_duplicate_emails,
            reverse_code=reverse_migration,
        ),
        # Step 2: Verify no non-empty duplicates remain before applying constraint
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
