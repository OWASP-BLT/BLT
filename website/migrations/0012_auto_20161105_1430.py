# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-11-05 18:30


from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('website', '0011_auto_20161105_1428'),
    ]

    operations = [
        migrations.AddField(
            model_name='points',
            name='created',
            field=models.DateTimeField(auto_now_add=True, default='2016-12-12 12:12:12'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='points',
            name='modified',
            field=models.DateTimeField(auto_now=True, default='2016-12-12 12:12:12'),
            preserve_default=False,
        ),
    ]
