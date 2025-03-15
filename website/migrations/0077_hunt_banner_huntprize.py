# Generated by Django 4.1 on 2023-07-24 09:29

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0076_issue_team_members"),
    ]

    operations = [
        migrations.AddField(
            model_name="hunt",
            name="banner",
            field=models.ImageField(blank=True, null=True, upload_to="banners"),
        ),
        migrations.CreateModel(
            name="HuntPrize",
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
                ("name", models.CharField(max_length=50)),
                ("value", models.PositiveIntegerField(default=0)),
                ("no_of_eligible_projects", models.PositiveIntegerField(default=1)),
                ("valid_submissions_eligible", models.BooleanField(default=False)),
                ("prize_in_crypto", models.BooleanField(default=False)),
                ("description", models.TextField(blank=True, null=True)),
                (
                    "hunt",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="website.hunt"),
                ),
            ],
        ),
    ]

