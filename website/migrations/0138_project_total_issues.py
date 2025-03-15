from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0137_project_release_datetime_project_release_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="total_issues",
            field=models.IntegerField(default=0),
        ),
    ]

