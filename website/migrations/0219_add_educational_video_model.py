from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0218_auto_20210915_1234'),
    ]

    operations = [
        migrations.CreateModel(
            name='EducationalVideo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField()),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('is_educational', models.BooleanField(default=False)),
            ],
        ),
    ]
