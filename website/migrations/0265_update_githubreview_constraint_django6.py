# Generated migration for Django 6.0 compatibility - updating CheckConstraint API
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0263_githubissue_githubissue_pr_merged_idx_and_more"),
    ]

    operations = [
        # Remove the old constraint with 'check' parameter (Django 5.x)
        migrations.RemoveConstraint(
            model_name="githubreview",
            name="at_least_one_reviewer",
        ),
        # Add the new constraint with 'condition' parameter (Django 6.0)
        migrations.AddConstraint(
            model_name="githubreview",
            constraint=models.CheckConstraint(
                condition=models.Q(reviewer__isnull=False)
                | models.Q(reviewer_contributor__isnull=False),
                name="at_least_one_reviewer",
            ),
        ),
    ]
