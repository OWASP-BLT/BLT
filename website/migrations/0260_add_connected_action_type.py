# Generated manually for GitHub OAuth BACON rewards feature

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('website', '0259_add_search_history'),
    ]

    operations = [
        migrations.AlterField(
            model_name='activity',
            name='action_type',
            field=models.CharField(
                max_length=20,
                choices=[
                    ('create', 'Created'),
                    ('update', 'Updated'),
                    ('delete', 'Deleted'),
                    ('signup', 'Signed Up'),
                    ('connected', 'Connected'),
                ],
            ),
        ),
    ]
