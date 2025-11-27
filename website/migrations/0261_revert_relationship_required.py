# Generated migration to make relationship required again

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0260_make_relationship_optional"),
    ]

    operations = [
        migrations.AlterField(
            model_name="recommendation",
            name="relationship",
            field=models.CharField(
                choices=[
                    ("colleague", "Colleague"),
                    ("mentor", "Mentor"),
                    ("bug_hunter", "Bug Hunter"),
                    ("team_member", "Team Member"),
                    ("other", "Other"),
                ],
                default="colleague",
                help_text="Relationship between recommender and recipient",
                max_length=20,
            ),
        ),
    ]
