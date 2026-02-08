# Generated migration for TimeLog pause/resume functionality

from datetime import timedelta

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0263_githubissue_githubissue_pr_merged_idx_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="timelog",
            name="github_issue_number",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="timelog",
            name="github_repo",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="timelog",
            name="is_paused",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="timelog",
            name="paused_duration",
            field=models.DurationField(blank=True, default=timedelta, null=True),
        ),
        migrations.AddField(
            model_name="timelog",
            name="last_pause_time",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
