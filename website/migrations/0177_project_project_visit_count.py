# Generated by Django 5.1.4 on 2025-01-01 20:15

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0176_repo_contributor_repo_contributor_count_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="project_visit_count",
            field=models.IntegerField(default=0),
        ),
    ]