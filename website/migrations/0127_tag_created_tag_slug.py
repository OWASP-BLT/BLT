# Generated by Django 5.0.7 on 2024-08-10 19:41

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0126_alter_userprofile_subscribed_domains_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="tag",
            name="created",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="tag",
            name="slug",
            field=models.SlugField(default="", unique=True),
            preserve_default=False,
        ),
    ]

