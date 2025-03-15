# Generated by Django 5.1.3 on 2024-11-25 17:38

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0156_merge_20241124_0722"),
    ]

    operations = [
        migrations.AddField(
            model_name="timelog",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="organization",
                to="website.company",
            ),
        ),
        migrations.AlterField(
            model_name="company",
            name="url",
            field=models.URLField(unique=True),
        ),
    ]

