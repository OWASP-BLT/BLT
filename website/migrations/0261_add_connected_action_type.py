# Generated manually for GitHub OAuth BACON rewards feature

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0260_add_username_to_slackbotactivity"),
    ]

    operations = [
        migrations.AlterField(
            model_name="activity",
            name="action_type",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("create", "Created"),
                    ("update", "Updated"),
                    ("delete", "Deleted"),
                    ("signup", "Signed Up"),
                    ("connected", "Connected"),
                ],
            ),
        ),
    ]
