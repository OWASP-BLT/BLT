from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0134_blocked_modified"),
    ]

    operations = [
        migrations.AddField(
            model_name="project",
            name="stars",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="project",
            name="forks",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="project",
            name="external_links",
            field=models.JSONField(default=list, blank=True),
        ),
    ]
