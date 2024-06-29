# Generated by Django 5.0.6 on 2024-06-29 16:11

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0093_bid_bch_address"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="company_id",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
