# Generated by Django 5.1.3 on 2024-12-15 18:44

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0169_dailystatusreport_current_mood_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="company",
            name="trademark_check_date",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="company",
            name="trademark_count",
            field=models.IntegerField(default=0),
        ),
    ]
