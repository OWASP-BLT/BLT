# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2017-07-08 21:22


import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('website', '0029_userprofile_title'),
    ]

    operations = [
        migrations.AddField(
            model_name='issue',
            name='closed_by',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE,
                                    related_name='closed_by', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='issue',
            name='closed_date',
            field=models.DateTimeField(default=None, blank=True, null=True),
        ),
    ]
