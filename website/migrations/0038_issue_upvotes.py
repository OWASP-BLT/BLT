# Generated by Django 1.11.1 on 2017-08-17 01:43


from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0037_auto_20170813_0319"),
    ]

    operations = [
        migrations.AddField(
            model_name="issue",
            name="upvotes",
            field=models.IntegerField(default=0),
        ),
    ]

