# Generated manually for Easter egg models

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("website", "0255_add_reviewer_contributor"),
    ]

    operations = [
        migrations.CreateModel(
            name="EasterEgg",
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
                ("name", models.CharField(max_length=100, unique=True)),
                (
                    "code",
                    models.CharField(
                        max_length=50,
                        unique=True,
                        help_text="Unique code identifier for the Easter egg",
                    ),
                ),
                (
                    "description",
                    models.TextField(help_text="Description of the Easter egg"),
                ),
                (
                    "reward_type",
                    models.CharField(
                        max_length=20,
                        choices=[
                            ("bacon", "BACON Token"),
                            ("badge", "Badge"),
                            ("points", "Points"),
                            ("fun", "Just for Fun"),
                        ],
                        default="fun",
                    ),
                ),
                (
                    "reward_amount",
                    models.IntegerField(
                        default=0, help_text="Amount of reward (if applicable)"
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                (
                    "max_claims_per_user",
                    models.IntegerField(
                        default=1,
                        help_text="Maximum times a user can claim this Easter egg (0 = unlimited)",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Easter Egg",
                "verbose_name_plural": "Easter Eggs",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="EasterEggDiscovery",
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
                ("discovered_at", models.DateTimeField(auto_now_add=True)),
                (
                    "ip_address",
                    models.GenericIPAddressField(null=True, blank=True),
                ),
                (
                    "user_agent",
                    models.CharField(max_length=255, null=True, blank=True),
                ),
                (
                    "easter_egg",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="discoveries",
                        to="website.easteregg",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="easter_egg_discoveries",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Easter Egg Discovery",
                "verbose_name_plural": "Easter Egg Discoveries",
                "ordering": ["-discovered_at"],
            },
        ),
        migrations.AddIndex(
            model_name="eastereggdiscovery",
            index=models.Index(
                fields=["user", "discovered_at"], name="website_eas_user_id_6c8d7f_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="eastereggdiscovery",
            index=models.Index(
                fields=["easter_egg", "discovered_at"],
                name="website_eas_easter__e8b9e4_idx",
            ),
        ),
        migrations.AlterUniqueTogether(
            name="eastereggdiscovery",
            unique_together={("user", "easter_egg")},
        ),
    ]
