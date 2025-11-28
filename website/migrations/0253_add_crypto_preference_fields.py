# Generated migration for adding cryptocurrency preference fields

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0252_add_adventure_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="preferred_cryptocurrency",
            field=models.CharField(
                max_length=10,
                choices=[
                    ("ETH", "Ethereum (ETH)"),
                    ("BTC", "Bitcoin (BTC)"),
                    ("BCH", "Bitcoin Cash (BCH)"),
                ],
                default="ETH",
                help_text="Preferred cryptocurrency for receiving rewards",
            ),
        ),
        migrations.AddField(
            model_name="issue",
            name="blockchain_tx_hash",
            field=models.CharField(
                max_length=66,
                blank=True,
                null=True,
                help_text="Ethereum transaction hash for reward distribution (0x + 64 hex chars)",
            ),
        ),
        migrations.AddField(
            model_name="issue",
            name="reward_distributed_at",
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text="Timestamp when reward was distributed via blockchain",
            ),
        ),
    ]
