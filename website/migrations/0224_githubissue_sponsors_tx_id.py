# Generated by Django 5.1.6 on 2025-03-10 01:51

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0223_githubissue_has_dollar_tag"),
    ]

    operations = [
        migrations.AddField(
            model_name="githubissue",
            name="sponsors_tx_id",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]

