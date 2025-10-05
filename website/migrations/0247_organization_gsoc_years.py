# Generated migration to add gsoc_years field to Organization model

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0246_add_user_progress_models"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="gsoc_years",
            field=models.CharField(
                blank=True,
                max_length=255,
                null=True,
                help_text="Comma-separated list of years participated in Google Summer of Code",
            ),
        ),
    ]
