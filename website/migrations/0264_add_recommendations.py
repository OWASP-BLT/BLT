# Generated manually for recommendations feature

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("website", "0263_githubissue_githubissue_pr_merged_idx_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="RecommendationSkill",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
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
                "ordering": ("category", "name"),
            },
        ),
        migrations.CreateModel(
            name="Recommendation",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
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
                    models.JSONField(
                        blank=True, default=list, help_text="List of skill names endorsed in this recommendation"
                    ),
                ),
                (
                    "is_visible",
                    models.BooleanField(
                        default=True, help_text="Whether this recommendation is visible on the profile"
                    ),
                ),
                (
                    "is_approved",
                    models.BooleanField(
                        default=False, help_text="Whether the recipient has approved this recommendation"
                    ),
                ),
                (
                    "is_highlighted",
                    models.BooleanField(
                        default=False, help_text="Whether this recommendation is highlighted/pinned on the profile"
                    ),
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
                "ordering": ("-created_at",),
                "unique_together": (("from_user", "to_user"),),
            },
        ),
        migrations.AddField(
            model_name="userprofile",
            name="recommendation_blurb",
            field=models.TextField(
                blank=True,
                help_text="Short summary/about section for recommendations (max 500 characters).",
                max_length=500,
                null=True,
            ),
        ),
        migrations.CreateModel(
            name="RecommendationRequest",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "message",
                    models.TextField(
                        blank=True, help_text="Optional message from requester", max_length=500, null=True
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("accepted", "Accepted"),
                            ("declined", "Declined"),
                            ("completed", "Completed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="pending",
                        help_text="Status of the recommendation request",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("responded_at", models.DateTimeField(blank=True, null=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "from_user",
                    models.ForeignKey(
                        help_text="User requesting the recommendation",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="recommendation_requests_sent",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "to_user",
                    models.ForeignKey(
                        help_text="User being asked to write the recommendation",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="recommendation_requests_received",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name": "Recommendation Request",
                "verbose_name_plural": "Recommendation Requests",
                "ordering": ("-created_at",),
                "unique_together": (("from_user", "to_user"),),
            },
        ),
        migrations.AddField(
            model_name="recommendation",
            name="request",
            field=models.ForeignKey(
                blank=True,
                help_text="The recommendation request that led to this recommendation (if any)",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="recommendation",
                to="website.recommendationrequest",
            ),
        ),
        migrations.AddIndex(
            model_name="recommendation",
            index=models.Index(fields=["to_user", "is_approved", "is_visible"], name="rec_to_user_app_vis_idx"),
        ),
        migrations.AddIndex(
            model_name="recommendation",
            index=models.Index(fields=["from_user"], name="rec_from_user_idx"),
        ),
        migrations.AddIndex(
            model_name="recommendationrequest",
            index=models.Index(fields=["to_user", "status"], name="rec_req_to_user_status_idx"),
        ),
        migrations.AddIndex(
            model_name="recommendationrequest",
            index=models.Index(fields=["from_user"], name="rec_req_from_user_idx"),
        ),
    ]
