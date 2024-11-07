# Generated by Django 5.1.2 on 2024-11-07 09:25

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0141_project_project_visit_count_project_repo_visit_count"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="IpReport",
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
                ("activity_title", models.CharField(max_length=255)),
                (
                    "activity_type",
                    models.CharField(
                        choices=[("malicious", "Malicious"), ("friendly", "Friendly")],
                        max_length=50,
                    ),
                ),
                ("ip_address", models.GenericIPAddressField()),
                (
                    "ip_type",
                    models.CharField(choices=[("ipv4", "IPv4"), ("ipv6", "IPv6")], max_length=10),
                ),
                ("description", models.TextField()),
                ("created", models.DateTimeField(auto_now_add=True)),
                (
                    "reporter_ip_address",
                    models.GenericIPAddressField(blank=True, null=True),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
