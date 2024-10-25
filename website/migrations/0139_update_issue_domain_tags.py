from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('website', '0138_project_last_updated'),
    ]

    operations = [
        migrations.AddField(
            model_name='issue',
            name='tags',
            field=models.ManyToManyField(to='website.Tag', blank=True),
        ),
        migrations.AddField(
            model_name='domain',
            name='tags',
            field=models.ManyToManyField(to='website.Tag', blank=True),
        ),
        migrations.AddField(
            model_name='project',
            name='tags',
            field=models.ManyToManyField(to='website.Tag', blank=True),
        ),
        migrations.AddField(
            model_name='company',
            name='tags',
            field=models.ManyToManyField(to='website.Tag', blank=True),
        ),
    ]
