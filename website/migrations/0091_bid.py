# Generated by Django 5.0.2 on 2024-05-09 19:44

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0090_alter_domain_managers"),
    ]

    operations = [
        migrations.CreateModel(
            name="Bid",
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
                ("issue_url", models.URLField()),
                (
                    "user",
                    models.CharField(blank=True, default="Add user", max_length=30, null=True),
                ),
                ("created", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "modified",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                ("amount", models.IntegerField()),
                ("status", models.CharField(default="Open", max_length=10)),
                ("pr_link", models.URLField(blank=True, null=True)),
                ("bch_address", models.CharField(blank=True, null=True, max_length=45)),
            ],
        ),
    ]
