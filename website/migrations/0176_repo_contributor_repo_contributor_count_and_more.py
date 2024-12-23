# Generated by Django 5.1.3 on 2024-12-23 23:06

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0175_remove_project_closed_issues_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="repo",
            name="Contributor",
            field=models.ManyToManyField(
                blank=True, related_name="repos", to="website.contributor"
            ),
        ),
        migrations.AddField(
            model_name="repo",
            name="contributor_count",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="repo",
            name="release_datetime",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="repo",
            name="release_name",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
