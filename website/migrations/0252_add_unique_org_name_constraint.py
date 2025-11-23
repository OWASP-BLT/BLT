# Generated manually for security improvements

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0251_add_fields_to_management_command_log"),
    ]

    operations = [
        migrations.AddIndex(
            model_name="organization",
            index=models.Index(fields=["name"], name="org_name_idx"),
        ),
        migrations.AddConstraint(
            model_name="organization",
            constraint=models.UniqueConstraint(fields=["name"], name="unique_organization_name"),
        ),
    ]
