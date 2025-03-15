from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0200_add_organization_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="address_line_1",
            field=models.CharField(
                max_length=255, blank=True, null=True, help_text="The primary address of the organization"
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="address_line_2",
            field=models.CharField(
                max_length=255, blank=True, null=True, help_text="Additional address details (optional)"
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="city",
            field=models.CharField(
                max_length=100, blank=True, null=True, help_text="The city where the organization is located"
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="state",
            field=models.CharField(
                max_length=100, blank=True, null=True, help_text="The state or region of the organization"
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="country",
            field=models.CharField(max_length=100, blank=True, null=True, help_text="The country of the organization"),
        ),
        migrations.AddField(
            model_name="organization",
            name="postal_code",
            field=models.CharField(max_length=20, blank=True, null=True, help_text="ZIP code or postal code"),
        ),
        migrations.AddField(
            model_name="organization",
            name="latitude",
            field=models.DecimalField(
                max_digits=9, decimal_places=6, blank=True, null=True, help_text="The latitude coordinate"
            ),
        ),
        migrations.AddField(
            model_name="organization",
            name="longitude",
            field=models.DecimalField(
                max_digits=9, decimal_places=6, blank=True, null=True, help_text="The longitude coordinate"
            ),
        ),
    ]

