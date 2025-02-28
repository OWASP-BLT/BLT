from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0209_repo_organization"),
    ]

    operations = [
        migrations.AddField(
            model_name="repo",
            name="is_owasp_repo",
            field=models.BooleanField(default=False),
        ),
    ]
