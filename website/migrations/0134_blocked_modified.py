# Generated by Django 5.0.7 on 2024-08-13 18:22

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0133_alter_blocked_created"),
    ]

    operations = [
        migrations.AddField(
            model_name="blocked",
            name="modified",
            field=models.DateTimeField(auto_now=True),
        ),
    ]

