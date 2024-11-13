# Generated by Django 5.1.1 on 2024-11-09 23:21

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0141_project_project_visit_count_project_repo_visit_count"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="contributorstats",
            name="last_updated",
        ),
        migrations.AddField(
            model_name="contributorstats",
            name="github_date",
            field=models.DateField(default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="contributorstats",
            name="username",
            field=models.CharField(max_length=255),
        ),
    ]
