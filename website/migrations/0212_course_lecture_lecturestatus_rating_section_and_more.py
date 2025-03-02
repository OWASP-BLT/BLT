# Generated by Django 5.1.4 on 2025-02-27 23:53

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0211_alter_githubreview_review_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="Course",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField()),
                ("thumbnail", models.ImageField(blank=True, null=True, upload_to="course_thumbnails/")),
                (
                    "level",
                    models.CharField(
                        choices=[("BEG", "Beginner"), ("INT", "Intermediate"), ("ADV", "Advanced")],
                        default="BEG",
                        max_length=3,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "instructor",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="courses_teaching",
                        to="website.userprofile",
                    ),
                ),
                ("tags", models.ManyToManyField(blank=True, related_name="courses", to="website.tag")),
            ],
        ),
        migrations.CreateModel(
            name="Lecture",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True, null=True)),
                (
                    "content_type",
                    models.CharField(
                        choices=[
                            ("VIDEO", "Video Lecture"),
                            ("LIVE", "Live Session"),
                            ("DOCUMENT", "Document"),
                            ("QUIZ", "Quiz"),
                        ],
                        max_length=10,
                    ),
                ),
                ("video_url", models.URLField(blank=True, null=True)),
                ("live_url", models.URLField(blank=True, null=True)),
                ("scheduled_time", models.DateTimeField(blank=True, null=True)),
                ("recording_url", models.URLField(blank=True, null=True)),
                ("content", models.TextField()),
                ("duration", models.PositiveIntegerField(blank=True, help_text="Duration in minutes", null=True)),
                ("order", models.PositiveIntegerField()),
                (
                    "instructor",
                    models.ForeignKey(
                        blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="website.userprofile"
                    ),
                ),
                ("tags", models.ManyToManyField(blank=True, related_name="lectures", to="website.tag")),
            ],
            options={
                "ordering": ["order"],
            },
        ),
        migrations.CreateModel(
            name="LectureStatus",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "status",
                    models.CharField(choices=[("PROGRESS", "In Progress"), ("COMPLETED", "Completed")], max_length=15),
                ),
                (
                    "lecture",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lecture_statuses",
                        to="website.lecture",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="student", to="website.userprofile"
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Rating",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "score",
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=3,
                        validators=[
                            django.core.validators.MinValueValidator(0.0),
                            django.core.validators.MaxValueValidator(5.0),
                        ],
                    ),
                ),
                ("comment", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="ratings", to="website.course"
                    ),
                ),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="website.userprofile")),
            ],
        ),
        migrations.CreateModel(
            name="Section",
            fields=[
                ("id", models.AutoField(auto_created=True, primary key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("description", models.TextField(blank=True, null=True)),
                ("order", models.PositiveIntegerField()),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="sections", to="website.course"
                    ),
                ),
            ],
            options={
                "ordering": ["order"],
            },
        ),
        migrations.AddField(
            model_name="lecture",
            name="section",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="lectures",
                to="website.section",
            ),
        ),
        migrations.CreateModel(
            name="Enrollment",
            fields=[
                ("id", models.AutoField(auto_created=True, primary key=True, serialize=False, verbose_name="ID")),
                ("enrolled_at", models.DateTimeField(auto_now_add=True)),
                ("completed", models.BooleanField(default=False)),
                ("last_accessed", models.DateTimeField(auto_now=True)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, related_name="enrollments", to="website.course"
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="enrollments",
                        to="website.userprofile",
                    ),
                ),
            ],
            options={
                "unique_together": {("student", "course")},
            },
        ),
    ]
