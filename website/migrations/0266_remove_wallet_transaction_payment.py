# Generated manually

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0265_delete_bannedapp"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="payment",
            name="wallet",
        ),
        migrations.RemoveField(
            model_name="transaction",
            name="wallet",
        ),
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
