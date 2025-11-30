# Generated migration for adding GitHub integration fields to Issue model

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0258_add_slackchannel_model"),
    ]

    operations = [
        migrations.AddField(
            model_name="issue",
            name="github_comment_count",
            field=models.IntegerField(default=0, help_text="Number of comments on the GitHub issue"),
        ),
        migrations.AddField(
            model_name="issue",
            name="github_state",
            field=models.CharField(
                blank=True,
                default="",
                choices=[("open", "Open"), ("closed", "Closed")],
                help_text="Current state of the GitHub issue (open/closed) as reported by GitHub API",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="issue",
            name="github_fetch_status",
            field=models.BooleanField(
                default=False,
                help_text="Whether GitHub data was successfully fetched from the API",
            ),
        ),
        migrations.AddField(
            model_name="issue",
            name="github_last_fetched_at",
            field=models.DateTimeField(
                blank=True,
                help_text="Timestamp of when GitHub data was last fetched",
                null=True,
            ),
        ),
    ]
