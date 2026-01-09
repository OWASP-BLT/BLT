# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import swapper
from django.db import models, migrations
from decimal import Decimal
import model_utils.fields
import django.utils.timezone
from django.conf import settings

dependancies = [
    migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ('contenttypes', '0001_initial'),
]

swappable_dep = swapper.dependency('star_ratings', 'Rating')
if swappable_dep == migrations.swappable_dependency('star_ratings.Rating'):
    dependancies.append(swappable_dep)


class Migration(migrations.Migration):
    dependencies = dependancies

    operations = [
        migrations.CreateModel(
            name='Rating',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('count', models.PositiveIntegerField(default=0)),
                ('total', models.PositiveIntegerField(default=0)),
                ('average', models.DecimalField(decimal_places=3, max_digits=6, default=Decimal('0'))),
                ('object_id', models.PositiveIntegerField(blank=True, null=True)),
                ('content_type', models.ForeignKey(blank=True, null=True, to='contenttypes.ContentType', on_delete=models.CASCADE)),
            ],
            options={
                'swappable': swapper.swappable_setting('star_ratings', 'Rating')
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='UserRating',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('created', model_utils.fields.AutoCreatedField(verbose_name='created', editable=False, default=django.utils.timezone.now)),
                ('modified', model_utils.fields.AutoLastModifiedField(verbose_name='modified', editable=False, default=django.utils.timezone.now)),
                ('ip', models.GenericIPAddressField(blank=True, null=True)),
                ('score', models.PositiveSmallIntegerField()),
                ('rating', models.ForeignKey(related_name='user_ratings', to=swapper.get_model_name('star_ratings', 'Rating'), on_delete=models.CASCADE)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=models.CASCADE)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='userrating',
            unique_together=set([('user', 'rating')]),
        ),
        migrations.AlterUniqueTogether(
            name='rating',
            unique_together=set([('content_type', 'object_id')]),
        ),
    ]
