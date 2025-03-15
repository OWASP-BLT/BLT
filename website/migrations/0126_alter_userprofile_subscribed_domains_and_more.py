# Generated by Django 5.0.7 on 2024-08-10 16:40

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0125_activitylog_timelog"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="userprofile",
            name="subscribed_domains",
            field=models.ManyToManyField(blank=True, related_name="user_subscribed_domains", to="website.domain"),
        ),
        migrations.AlterField(
            model_name="userprofile",
            name="subscribed_users",
            field=models.ManyToManyField(
                blank=True,
                related_name="user_subscribed_users",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]

