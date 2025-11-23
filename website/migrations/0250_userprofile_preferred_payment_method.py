# Generated migration for preferred_payment_method field

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0249_merge_0247_job_0248_add_slack_fields_to_project"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="preferred_payment_method",
            field=models.CharField(
                blank=True,
                choices=[("sponsors", "GitHub Sponsors"), ("bch", "Bitcoin Cash")],
                default="sponsors",
                help_text="Preferred payment method for bounty payouts",
                max_length=20,
                null=True,
            ),
        ),
    ]
