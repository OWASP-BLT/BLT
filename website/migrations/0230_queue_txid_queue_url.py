# Generated by Django 5.1.6 on 2025-03-12 01:36

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0229_hackathon_sponsor_link_hackathon_sponsor_note"),
    ]

    operations = [
        migrations.AddField(
            model_name="queue",
            name="txid",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="queue",
            name="url",
            field=models.URLField(blank=True, null=True),
        ),
    ]
