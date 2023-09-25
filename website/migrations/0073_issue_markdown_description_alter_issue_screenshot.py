# Generated by Django 4.1 on 2023-05-20 12:48

from django.db import migrations, models
import website.models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0072_issue_is_hidden_userprofile_issues_hidden'),
    ]

    operations = [
        migrations.AddField(
            model_name='issue',
            name='markdown_description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='issue',
            name='screenshot',
            field=models.ImageField(blank=True, null=True, upload_to='screenshots', validators=[website.models.validate_image]),
        ),
    ]
