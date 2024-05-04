# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('tellme', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='feedback',
            name='browser',
            field=models.TextField(verbose_name='Browser'),
        ),
        migrations.AlterField(
            model_name='feedback',
            name='comment',
            field=models.TextField(verbose_name='Comment'),
        ),
        migrations.AlterField(
            model_name='feedback',
            name='created',
            field=models.DateTimeField(auto_now_add=True, verbose_name='Creation date'),
        ),
        migrations.AlterField(
            model_name='feedback',
            name='screenshot',
            field=models.ImageField(upload_to='tellme/screenshots/', verbose_name='Screenshot', blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='feedback',
            name='url',
            field=models.CharField(max_length=255, verbose_name='Url'),
        ),
        migrations.AlterField(
            model_name='feedback',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, blank=True, verbose_name='User', to=settings.AUTH_USER_MODEL, null=True),
        ),
    ]
