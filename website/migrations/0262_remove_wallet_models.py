# Generated manually to remove wallet, transaction, and payment models

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0261_add_connected_action_type"),
    ]

    operations = [
        migrations.DeleteModel(
            name="Payment",
        ),
        migrations.DeleteModel(
            name="Transaction",
        ),
        migrations.DeleteModel(
            name="Wallet",
        ),
    ]
