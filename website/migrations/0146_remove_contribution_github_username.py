# Generated by Django 5.1.1 on 2024-11-10 04:34

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0145_contribution_github_username_alter_contribution_user"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="contribution",
            name="github_username",
        ),
    ]

