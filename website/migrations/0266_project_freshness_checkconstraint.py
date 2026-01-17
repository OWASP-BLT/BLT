from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0265_project_contributors_alter_project_freshness"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="project",
            constraint=models.CheckConstraint(
                check=models.Q(freshness__gte=0) & models.Q(freshness__lte=100),
                name="freshness_0_100_range",
            ),
        ),
    ]
