# Generated by Django 4.1 on 2023-02-24 12:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("website", "0071_alter_issuescreenshot_issue"),
    ]

    operations = [
        migrations.AddField(
            model_name="issue",
            name="is_hidden",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="issues_hidden",
            field=models.BooleanField(default=False),
        ),
    ]
