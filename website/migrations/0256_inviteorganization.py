# Generated migration for InviteOrganization model

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("website", "0255_add_reviewer_contributor"),
    ]

    operations = [
        migrations.CreateModel(
            name="InviteOrganization",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254)),
                ("organization_name", models.CharField(blank=True, max_length=255)),
                ("referral_code", models.CharField(default=uuid.uuid4, editable=False, max_length=100, unique=True)),
                ("points_awarded", models.BooleanField(default=False)),
                ("created", models.DateTimeField(auto_now_add=True)),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="invites",
                        to="website.organization",
                    ),
                ),
                (
                    "sender",
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="sent_org_invites",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
