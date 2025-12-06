# Generated migration to remove staking models

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0245_merge_20250801_1858"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="stakingentry",
            name="pool",
        ),
        migrations.RemoveField(
            model_name="stakingentry",
            name="user",
        ),
        migrations.RemoveField(
            model_name="stakingpool",
            name="challenge",
        ),
        migrations.RemoveField(
            model_name="stakingpool",
            name="created_by",
        ),
        migrations.RemoveField(
            model_name="stakingpool",
            name="winner",
        ),
        migrations.RemoveField(
            model_name="stakingtransaction",
            name="pool",
        ),
        migrations.RemoveField(
            model_name="stakingtransaction",
            name="user",
        ),
        migrations.DeleteModel(
            name="StakingEntry",
        ),
        migrations.DeleteModel(
            name="StakingPool",
        ),
        migrations.DeleteModel(
            name="StakingTransaction",
        ),
    ]
