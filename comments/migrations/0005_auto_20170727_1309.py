# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-07-27 13:09


import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('comments', '0004_auto_20170727_1308'),
    ]

    operations = [
        migrations.AlterField(
            model_name='comment',
            name='parent',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, to='comments.Comment'),
        ),
    ]
