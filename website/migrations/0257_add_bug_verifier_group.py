# Generated migration for bug verifier group and permission

from django.db import migrations


def create_bug_verifier_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    Issue = apps.get_model("website", "Issue")

    # Get the content type for Issue model
    issue_content_type = ContentType.objects.get_for_model(Issue)

    # Create permission for verifying bugs
    permission, created = Permission.objects.get_or_create(
        codename="can_verify_bugs",
        content_type=issue_content_type,
        defaults={"name": "Can verify and publish bug reports"},
    )

    # Create the bug verifier group
    bug_verifier_group, created = Group.objects.get_or_create(name="Bug Verifiers")

    # Add the permission to the group
    bug_verifier_group.permissions.add(permission)


def remove_bug_verifier_group(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    # Remove the group
    Group.objects.filter(name="Bug Verifiers").delete()

    # Remove the permission
    Permission.objects.filter(codename="can_verify_bugs").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0256_inviteorganization"),
    ]

    operations = [
        migrations.RunPython(create_bug_verifier_group, remove_bug_verifier_group),
    ]
