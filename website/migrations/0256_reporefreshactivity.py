# Generated migration for RepoRefreshActivity model

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
            name="RepoRefreshActivity",
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
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                (
                    "issues_count",
                    models.IntegerField(
                        default=0,
                        help_text="Number of issues fetched during this refresh",
                    ),
                ),
                (
                    "prs_count",
                    models.IntegerField(
                        default=0,
                        help_text="Number of pull requests fetched during this refresh",
                    ),
                ),
                (
                    "success",
                    models.BooleanField(
                        default=True,
                        help_text="Whether the refresh completed successfully",
                    ),
                ),
                (
                    "repo",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="refresh_activities",
                        to="website.repo",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="repo_refresh_activities",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-timestamp"],
            },
        ),
        migrations.AddIndex(
            model_name="reporefreshactivity",
            index=models.Index(
                fields=["repo", "-timestamp"],
                name="website_rep_repo_id_b8e1d9_idx",
            ),
        ),
    ]
