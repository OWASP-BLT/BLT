# Generated by Django 5.1.7 on 2025-03-27 15:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0234_githubissue_linked_pull_requests'),
    ]

    operations = [
        migrations.AddField(
            model_name='baconsubmission',
            name='organization',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
