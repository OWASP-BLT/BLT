# Generated by Django 5.1.6 on 2025-02-22 03:30

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0207_rename_suggestioncategory_forumcategory_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="points",
            name="created",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]
