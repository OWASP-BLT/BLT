# Generated by Django 5.0.3 on 2024-03-06 07:39

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0083_alter_invitefriend_options_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ContributorStats",
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
                ("username", models.CharField(max_length=255, unique=True)),
                ("commits", models.IntegerField(default=0)),
                ("issues_opened", models.IntegerField(default=0)),
                ("issues_closed", models.IntegerField(default=0)),
                ("prs", models.IntegerField(default=0)),
                ("comments", models.IntegerField(default=0)),
                ("assigned_issues", models.IntegerField(default=0)),
                ("last_updated", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
