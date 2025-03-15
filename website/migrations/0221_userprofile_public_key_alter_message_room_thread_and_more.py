# Generated by Django 5.1.6 on 2025-03-06 16:40

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0220_alter_dailystats_name_alter_issue_label"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="public_key",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="message",
            name="room",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="messages",
                to="website.room",
            ),
        ),
        migrations.CreateModel(
            name="Thread",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("participants", models.ManyToManyField(related_name="threads", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name="message",
            name="thread",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="messages",
                to="website.thread",
            ),
        ),
    ]

