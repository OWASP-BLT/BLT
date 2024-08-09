# Generated by Django 5.0.7 on 2024-07-23 16:56

from django.db import migrations, models


class Migration(migrations.Migration):
    replaces = [
        ("website", "0096_moniterip"),
        ("website", "0097_rename_moniterip_monitorip"),
    ]

    dependencies = [
        ("website", "0095_company_description"),
    ]

    operations = [
        migrations.CreateModel(
            name="MonitorIP",
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
                ("ip", models.GenericIPAddressField(blank=True, null=True)),
                (
                    "user_agent",
                    models.CharField(blank=True, default="", max_length=255, null=True),
                ),
                ("count", models.IntegerField(default=1)),
            ],
        ),
    ]