# Generated manually to merge conflicting 0247 migrations

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0247_add_github_comment_leaderboard"),
        ("website", "0247_organization_github_org_gsoc_years"),
        ("website", "0249_merge_0247_job_0248_add_slack_fields_to_project"),
    ]

    operations = []
