# Generated by Django 5.1.7 on 2025-04-02 20:06

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0235_alter_lecture_content_alter_lecture_instructor"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ReminderSettings",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("reminder_time", models.TimeField(help_text="Time of day to send reminder (in user's timezone)")),
                ("timezone", models.CharField(default="UTC", help_text="User's timezone", max_length=50)),
                ("is_active", models.BooleanField(default=True, help_text="Whether reminders are enabled")),
                (
                    "last_reminder_sent",
                    models.DateTimeField(blank=True, help_text="When the last reminder was sent", null=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reminder_settings",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Reminder Settings",
                "verbose_name_plural": "Reminder Settings",
                "ordering": ["-created_at"],
            },
        ),
    ]
