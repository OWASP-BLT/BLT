# Generated by Django 5.1.3 on 2025-01-30 15:36

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0187_baconearning"),
    ]

    operations = [
        migrations.CreateModel(
            name="GitHubReview",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("review_id", models.IntegerField(unique=True)),
                ("body", models.TextField(blank=True, null=True)),
                ("state", models.CharField(max_length=50)),
                ("submitted_at", models.DateTimeField()),
                ("url", models.URLField()),
                (
                    "pull_request",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reviews",
                        to="website.githubissue",
                    ),
                ),
                (
                    "reviewer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reviews_made",
                        to="website.userprofile",
                    ),
                ),
            ],
        ),
    ]

