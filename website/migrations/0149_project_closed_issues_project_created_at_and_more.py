# Generated by Django 5.1.1 on 2024-11-10 05:25

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0148_project_last_commit_date_project_license_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="closed_issues",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="project",
            name="created_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="project",
            name="network_count",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="project",
            name="open_issues",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="project",
            name="size",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="project",
            name="subscribers_count",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="project",
            name="updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
