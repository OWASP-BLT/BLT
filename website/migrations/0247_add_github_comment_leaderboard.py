# Generated manually for adding GitHub comment leaderboard

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0246_add_user_progress_models"),
    ]

    operations = [
        migrations.CreateModel(
            name="GitHubComment",
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
                ("comment_id", models.BigIntegerField(unique=True)),
                ("body", models.TextField()),
                (
                    "comment_type",
                    models.CharField(
                        choices=[
                            ("issue", "Issue Comment"),
                            ("pull_request", "Pull Request Comment"),
                            ("discussion", "Discussion Comment"),
                        ],
                        default="issue",
                        max_length=50,
                    ),
                ),
                ("created_at", models.DateTimeField()),
                ("updated_at", models.DateTimeField()),
                ("url", models.URLField()),
                (
                    "github_issue",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="comments",
                        to="website.githubissue",
                    ),
                ),
                (
                    "user_profile",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="github_comments",
                        to="website.userprofile",
                    ),
                ),
                (
                    "contributor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="github_comments",
                        to="website.contributor",
                    ),
                ),
                (
                    "repo",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="github_comments",
                        to="website.repo",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="githubcomment",
            index=models.Index(fields=["comment_id"], name="website_git_comment_idx"),
        ),
        migrations.AddIndex(
            model_name="githubcomment",
            index=models.Index(
                fields=["user_profile", "-created_at"],
                name="website_git_user_pr_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="githubcomment",
            index=models.Index(
                fields=["contributor", "-created_at"],
                name="website_git_contrib_idx",
            ),
        ),
    ]
