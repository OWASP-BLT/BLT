# Generated by Django 3.0.8 on 2020-08-19 06:57

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0059_transaction_wallet"),
    ]

    operations = [
        migrations.AddField(
            model_name="wallet",
            name="account_id",
            field=models.TextField(blank=True, null=True),
        ),
    ]

