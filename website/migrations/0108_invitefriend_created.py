# Generated by Django 5.0.7 on 2024-08-04 18:29

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0107_winner_created"),
    ]

    operations = [
        migrations.AddField(
            model_name="invitefriend",
            name="created",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]

