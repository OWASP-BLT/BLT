# -*- coding: utf-8 -*-
# Generated by Django 1.9.2 on 2016-09-09 23:02


from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('website', '0004_auto_20160903_2344'),
    ]

    operations = [
        migrations.AddField(
            model_name='hunt',
            name='color',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.AlterField(
            model_name='hunt',
            name='logo',
            field=models.ImageField(blank=True, null=True, upload_to=b'logos'),
        ),
    ]
