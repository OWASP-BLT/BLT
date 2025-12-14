# Generated manually for monthly visitor leaderboard feature

from typing import ClassVar

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies: ClassVar[list[tuple[str, str]]] = [
        ("website", "0261_add_connected_action_type"),
    ]

    operations: ClassVar[list[migrations.operations.base.Operation]] = [
        migrations.AddField(
            model_name="userprofile",
            name="monthly_visit_count",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Count of visits in current month",
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="last_monthly_visit",
            field=models.DateField(
                blank=True,
                null=True,
                help_text="Last day of monthly visit tracking",
            ),
        ),
    ]
