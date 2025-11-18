# Generated migration for adding reviewer_contributor field to GitHubReview
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0248_add_slack_fields_to_project"),
    ]

    operations = [
        # Make reviewer nullable
        migrations.AlterField(
            model_name="githubreview",
            name="reviewer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reviews_made_as_user",
                to="website.userprofile",
            ),
        ),
        # Add reviewer_contributor field
        migrations.AddField(
            model_name="githubreview",
            name="reviewer_contributor",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reviews_made_as_contributor",
                to="website.contributor",
            ),
        ),
    ]
