from django.db import migrations, models


def forwards(apps, schema_editor):
    Room = apps.get_model("website", "Room")
    Room.objects.filter(type="org").update(type="organization")


def backwards(apps, schema_editor):
    Room = apps.get_model("website", "Room")
    Room.objects.filter(type="organization").update(type="org")


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0266_alter_usertasksubmission_proof_url_delete_post"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
        migrations.AlterField(
            model_name="room",
            name="type",
            field=models.CharField(
                choices=[
                    ("project", "Project"),
                    ("bug", "Bug"),
                    ("organization", "Organization"),
                    ("custom", "Custom"),
                ],
                max_length=20,
            ),
        ),
    ]
