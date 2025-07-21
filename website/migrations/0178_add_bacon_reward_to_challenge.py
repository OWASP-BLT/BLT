# Generated manually for adding bacon_reward field to Challenge model

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0177_alter_challenge_team_participants"),
    ]

    operations = [
        migrations.AddField(
            model_name="challenge",
            name="bacon_reward",
            field=models.IntegerField(default=5),
        ),
    ]
