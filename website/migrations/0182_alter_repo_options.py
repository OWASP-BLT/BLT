# Generated by Django 5.1.4 on 2025-01-17 07:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0181_project_slack_url"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="repo",
            options={"ordering": ["-created"]},
        ),
    ]
