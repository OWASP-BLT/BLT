# Generated by Django 5.1.6 on 2025-03-02 12:14

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0213_organization_categories_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="organization",
            name="twitter",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
    ]
