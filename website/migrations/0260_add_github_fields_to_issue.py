# Generated migration for adding GitHub integration fields to Issue model

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0259_add_domain_slug"),
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
                choices=[("open", "Open"), ("closed", "Closed")],
                help_text="Current state of the GitHub issue",
                max_length=10,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="issue",
            name="github_fetch_status",
            field=models.BooleanField(default=False, help_text="Whether GitHub data was successfully fetched"),
        ),
    ]
