# Generated by Django 5.1.6 on 2025-03-13 09:57

import uuid

import django.db.models.deletion
import mdeditor.fields
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0232_bannedapp"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Newsletter",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("slug", models.SlugField(blank=True, unique=True)),
                ("content", mdeditor.fields.MDTextField(help_text="Write newsletter content in Markdown format")),
                ("featured_image", models.ImageField(blank=True, null=True, upload_to="newsletter_images")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("published_at", models.DateTimeField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("draft", "Draft"), ("published", "Published")], default="draft", max_length=10
                    ),
                ),
                ("recent_bugs_section", models.BooleanField(default=True, help_text="Include recently reported bugs")),
                ("leaderboard_section", models.BooleanField(default=True, help_text="Include leaderboard updates")),
                ("reported_ips_section", models.BooleanField(default=False, help_text="Include recently reported IPs")),
                ("email_subject", models.CharField(blank=True, max_length=255, null=True)),
                ("email_sent", models.BooleanField(default=False)),
                ("email_sent_at", models.DateTimeField(blank=True, null=True)),
                ("view_count", models.PositiveIntegerField(default=0)),
            ],
            options={
                "verbose_name": "Newsletter",
                "verbose_name_plural": "Newsletters",
                "ordering": ["-published_at"],
            },
        ),
        migrations.CreateModel(
            name="NewsletterSubscriber",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254, unique=True)),
                ("name", models.CharField(blank=True, max_length=100, null=True)),
                ("subscribed_at", models.DateTimeField(auto_now_add=True)),
                ("is_active", models.BooleanField(default=True)),
                ("confirmation_token", models.UUIDField(default=uuid.uuid4, editable=False)),
                ("confirmed", models.BooleanField(default=False)),
                ("wants_bug_reports", models.BooleanField(default=True)),
                ("wants_leaderboard_updates", models.BooleanField(default=True)),
                ("wants_security_news", models.BooleanField(default=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="newsletter_subscriptions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Newsletter Subscriber",
                "verbose_name_plural": "Newsletter Subscribers",
            },
        ),
    ]
