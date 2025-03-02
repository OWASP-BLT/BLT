# Generated by Django 5.1.6 on 2025-03-02 14:12

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0211_alter_githubreview_review_id"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="categories",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=100), blank=True, default=list, size=None
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="contributor_guidance_url",
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="organization",
            name="ideas_link",
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="organization",
            name="license",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="organization",
            name="source_code",
            field=models.URLField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="organization",
            name="tagline",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="organization",
            name="tech_tags",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=100), blank=True, default=list, size=None
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="topic_tags",
            field=django.contrib.postgres.fields.ArrayField(
                base_field=models.CharField(max_length=100), blank=True, default=list, size=None
            ),
        ),
    ]
