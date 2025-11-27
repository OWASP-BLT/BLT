# Generated manually for recommendations feature

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("website", "0257_project_slack_user_count"),
    ]

    operations = [
        migrations.CreateModel(
            name="RecommendationSkill",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                (
                    "category",
                    models.CharField(
                        choices=[("technical", "Technical"), ("soft_skills", "Soft Skills"), ("security", "Security")],
                        default="technical",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "Recommendation Skill",
                "verbose_name_plural": "Recommendation Skills",
                "ordering": ["category", "name"],
            },
        ),
        migrations.CreateModel(
            name="Recommendation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "relationship",
                    models.CharField(
                        choices=[
                            ("colleague", "Colleague"),
                            ("mentor", "Mentor"),
                            ("bug_hunter", "Bug Hunter"),
                            ("team_member", "Team Member"),
                            ("other", "Other"),
                        ],
                        default="colleague",
                        help_text="Relationship between recommender and recipient",
                        max_length=20,
                    ),
                ),
                ("recommendation_text", models.TextField(help_text="The recommendation text (200-1000 characters)")),
                (
                    "skills_endorsed",
                    models.JSONField(blank=True, default=list, help_text="List of skill names endorsed in this recommendation"),
                ),
                (
                    "is_visible",
                    models.BooleanField(default=True, help_text="Whether this recommendation is visible on the profile"),
                ),
                (
                    "is_approved",
                    models.BooleanField(default=False, help_text="Whether the recipient has approved this recommendation"),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "from_user",
                    models.ForeignKey(
                        help_text="User who wrote the recommendation",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="recommendations_given",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "to_user",
                    models.ForeignKey(
                        help_text="User being recommended",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="recommendations_received",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Recommendation",
                "verbose_name_plural": "Recommendations",
                "ordering": ["-created_at"],
                "unique_together": {("from_user", "to_user")},
            },
        ),
        migrations.AddIndex(
            model_name="recommendation",
            index=models.Index(
                fields=["to_user", "is_approved", "is_visible"], name="rec_to_user_app_vis_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="recommendation",
            index=models.Index(fields=["from_user"], name="rec_from_user_idx"),
        ),
    ]

