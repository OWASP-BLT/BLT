# Generated by Django 5.1.1 on 2024-11-11 00:10

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0150_project_commit_count_project_latest_release"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="project",
            name="latest_release",
        ),
    ]

