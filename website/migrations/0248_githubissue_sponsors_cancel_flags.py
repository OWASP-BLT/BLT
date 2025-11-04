from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0247_userprofile_preferred_payment_method"),
    ]

    operations = [
        migrations.AddField(
            model_name="githubissue",
            name="sponsors_cancellation_failed",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="githubissue",
            name="sponsors_cancellation_attempts",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="githubissue",
            name="sponsors_cancellation_last_attempt",
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
