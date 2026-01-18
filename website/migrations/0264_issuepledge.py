# Generated migration for IssuePledge model

from decimal import Decimal

import django.core.validators
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import website.models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0263_githubissue_githubissue_pr_merged_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='IssuePledge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=8, max_digits=12, validators=[django.core.validators.MinValueValidator(Decimal('0.00000001'))])),
                ('bch_address', models.CharField(max_length=255, validators=[website.models.validate_bch_address])),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('paid', 'Paid'), ('refunded', 'Refunded')], default='pending', max_length=20)),
                ('txid', models.CharField(blank=True, max_length=255, null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('issue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pledges', to='website.issue')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Issue Pledge',
                'verbose_name_plural': 'Issue Pledges',
                'ordering': ['-created'],
            },
        ),
        migrations.AddIndex(
            model_name='issuepledge',
            index=models.Index(fields=['issue', 'status'], name='issuepledge_issue_status_idx'),
        ),
        migrations.AddIndex(
            model_name='issuepledge',
            index=models.Index(fields=['user', '-created'], name='issuepledge_user_created_idx'),
        ),
        migrations.AddIndex(
            model_name='issuepledge',
            index=models.Index(fields=['status', '-created'], name='issuepledge_status_created_idx'),
        ),
    ]
