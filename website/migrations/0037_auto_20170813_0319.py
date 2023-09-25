# -*- coding: utf-8 -*-
# Generated by Django 1.11.1 on 2017-08-13 03:19


from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('website', '0036_auto_20170813_0049'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='follows',
            field=models.ManyToManyField(blank=True, related_name='follower', to='website.UserProfile'),
        ),
    ]
