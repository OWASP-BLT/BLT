# Generated by Django 5.0.7 on 2024-07-29 09:17

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0098_merge_20240726_0001"),
    ]

    operations = [
        migrations.AddField(
            model_name="winner",
            name="prize",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="website.huntprize",
            ),
        ),
        migrations.AddField(
            model_name="winner",
            name="prize_amount",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6),
        ),
    ]

