# Generated by Django 5.1.6 on 2025-02-19 19:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0203_remove_organization_unique_organization_slug_and_more"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="organization",
            name="unique_organization_slug",
        ),
        migrations.RemoveIndex(
            model_name="domain",
            name="domain_org_idx",
        ),
        migrations.RemoveIndex(
            model_name="ip",
            name="ip_path_created_idx",
        ),
        migrations.RemoveIndex(
            model_name="issue",
            name="issue_domain_status_idx",
        ),
        migrations.RemoveIndex(
            model_name="organization",
            name="org_created_idx",
        ),
        migrations.RemoveIndex(
            model_name="project",
            name="project_org_idx",
        ),
        migrations.RemoveIndex(
            model_name="repo",
            name="repo_project_idx",
        ),
        migrations.AlterField(
            model_name="organization",
            name="slug",
            field=models.SlugField(blank=True, max_length=255, unique=True),
        ),
    ]
