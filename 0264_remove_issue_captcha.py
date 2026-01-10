from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('website', '0263_githubissue_githubissue_pr_merged_idx_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='issue',
            name='captcha',
        ),
    ]
  
