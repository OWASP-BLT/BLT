# Generated by Django 5.0.8 on 2024-08-13 16:54

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0129_blocked"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="role",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
