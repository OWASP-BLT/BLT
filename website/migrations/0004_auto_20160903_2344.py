# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-09-04 03:44


import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("website", "0003_auto_20160831_2326"),
    ]

    operations = [
        migrations.CreateModel(
            name="Hunt",
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
                ("url", models.URLField()),
                ("prize", models.IntegerField()),
                (
                    "logo",
                    models.ImageField(blank=True, null=True, upload_to=b"screenshots"),
                ),
                ("plan", models.CharField(max_length=10)),
                ("created", models.DateTimeField(auto_now_add=True)),
                ("modified", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AlterModelOptions(
            name="issue",
            options={"ordering": ["-created"]},
        ),
    ]
