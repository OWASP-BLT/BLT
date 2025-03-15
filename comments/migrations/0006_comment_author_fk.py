# Generated by Django 4.1 on 2023-08-29 04:22

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0080_alter_issue_team_members"),
        ("comments", "0005_auto_20170727_1309"),
    ]

    operations = [
        migrations.AddField(
            model_name="comment",
            name="author_fk",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="website.userprofile",
            ),
        ),
    ]

