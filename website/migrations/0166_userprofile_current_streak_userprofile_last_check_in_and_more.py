# Generated by Django 5.1.3 on 2024-12-04 23:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0165_add_badge_icons"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="current_streak",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="last_check_in",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="longest_streak",
            field=models.IntegerField(default=0),
        ),
    ]
