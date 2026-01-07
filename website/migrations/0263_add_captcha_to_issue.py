from django.db import migrations, models
import captcha.fields

class Migration(migrations.Migration):

    dependencies = [
        
        ('website', '0265_merge_2024...'), 
    ]

    operations = [
        migrations.AddField(
            model_name='issue',
            name='captcha',
            field=captcha.fields.ReCaptchaField(default=''),
        ),
    ]
