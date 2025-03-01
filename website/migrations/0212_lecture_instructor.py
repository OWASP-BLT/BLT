# Generated by Django 5.1.4 on 2025-02-28 15:38

import django.db.models.expressions
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0211_course_lecture_lecturestatus_rating_section_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="lecture",
            name="instructor",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.expressions.Case, to="website.userprofile"
            ),
        ),
    ]
