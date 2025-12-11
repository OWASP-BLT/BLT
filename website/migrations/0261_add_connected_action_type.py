# Generated manually for GitHub OAuth BACON rewards feature

from typing import ClassVar

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies: ClassVar[list[tuple[str, str]]] = [
        ("website", "0260_add_username_to_slackbotactivity"),
    ]

    operations: ClassVar[list[migrations.operations.base.Operation]] = [
        migrations.AlterField(
            model_name="activity",
            name="action_type",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("create", "Created"),
                    ("update", "Updated"),
                    ("delete", "Deleted"),
                    ("signup", "Signed Up"),
                    ("connected", "Connected"),
                ],
            ),
        ),
        migrations.CreateModel(
            name="SocialAccountReward",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "provider",
                    models.CharField(
                        max_length=30,
                        help_text="Social provider name (e.g., github, google, facebook)",
                    ),
                ),
                (
                    "rewarded_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Timestamp when the reward was granted",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                        help_text="User who received the reward",
                    ),
                ),
            ],
            options={
                "verbose_name": "Social Account Reward",
                "verbose_name_plural": "Social Account Rewards",
                "ordering": ["-rewarded_at"],
            },
        ),
        migrations.AddIndex(
            model_name="socialaccountreward",
            index=models.Index(fields=["user", "provider"], name="website_soc_user_id_provid_idx"),
        ),
        migrations.AddConstraint(
            model_name="socialaccountreward",
            constraint=models.UniqueConstraint(
                fields=["user", "provider"],
                name="unique_user_provider_reward",
            ),
        ),
    ]
