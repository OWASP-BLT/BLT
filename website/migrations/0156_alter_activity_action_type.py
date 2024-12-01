# Generated by Django 5.1.3 on 2024-11-24 13:10

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0155_merge_20241124_0242"),
    ]

    operations = [
        migrations.AlterField(
            model_name="activity",
            name="action_type",
            field=models.CharField(
                choices=[
                    ("create", "Created"),
                    ("update", "Updated"),
                    ("delete", "Deleted"),
                    ("signup", "Signed Up"),
                ],
                max_length=10,
            ),
        ),
    ]
