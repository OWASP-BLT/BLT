# Generated by Django 4.1 on 2022-12-09 11:45

import django.db.models.deletion
from django.db import migrations, models

import website.models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0069_userprofile_issue_flaged"),
    ]

    operations = [
        migrations.AlterField(
            model_name="issue",
            name="label",
            field=models.PositiveSmallIntegerField(
                choices=[
                    (0, "General"),
                    (1, "Number Error"),
                    (2, "Functional"),
                    (3, "Performance"),
                    (4, "Security"),
                    (5, "Typo"),
                    (6, "Design"),
                    (7, "Server Down"),
                ],
                default=0,
            ),
        ),
        migrations.CreateModel(
            name="IssueScreenshot",
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
                (
                    "image",
                    models.ImageField(
                        upload_to="screenshots",
                        validators=[website.models.validate_image],
                    ),
                ),
                (
                    "issue",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="website.issue"
                    ),
                ),
            ],
        ),
    ]
