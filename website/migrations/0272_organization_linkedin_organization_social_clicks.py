from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0271_make_email_unique_safe"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="linkedin",
            field=models.URLField(blank=True, null=True, help_text="LinkedIn profile URL"),
        ),
        migrations.AddField(
            model_name="organization",
            name="social_clicks",
            field=models.JSONField(
                default=dict,
                help_text="Track social media profile visits (Twitter, GitHub, LinkedIn, Facebook)",
            ),
        ),
    ]
