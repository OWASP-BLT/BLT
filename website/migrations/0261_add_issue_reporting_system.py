# Add user reporting system for suspicious bug reports

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("website", "0260_add_username_to_slackbotactivity"),
    ]

    operations = [
        migrations.CreateModel(
            name="IssueReport",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "reason",
                    models.CharField(
                        choices=[
                            ("spam", "Spam"),
                            ("duplicate", "Duplicate"),
                            ("fake", "Fake/Invalid"),
                            ("inappropriate", "Inappropriate Content"),
                            ("other", "Other"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "description",
                    models.TextField(help_text="Please provide details about why you're reporting this issue"),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending Review"),
                            ("reviewed", "Reviewed"),
                            ("resolved", "Resolved"),
                            ("dismissed", "Dismissed"),
                        ],
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("admin_notes", models.TextField(blank=True, help_text="Admin notes about this report")),
                (
                    "reported_issue",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="reports", to="website.issue"
                    ),
                ),
                (
                    "reporter",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="issue_reports",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_reports",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created"],
            },
        ),
        migrations.AlterUniqueTogether(
            name="issuereport",
            unique_together={("reporter", "reported_issue")},
        ),
    ]
