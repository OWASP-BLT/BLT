# Generated manually to add database indexes for fast trademark searches

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0252_add_adventure_models"),
    ]

    operations = [
        # Add db_index to keyword field
        migrations.AlterField(
            model_name="trademark",
            name="keyword",
            field=models.CharField(max_length=255, db_index=True),
        ),
        # Add db_index to registration_number field
        migrations.AlterField(
            model_name="trademark",
            name="registration_number",
            field=models.CharField(max_length=50, blank=True, null=True, db_index=True),
        ),
        # Add db_index to serial_number field
        migrations.AlterField(
            model_name="trademark",
            name="serial_number",
            field=models.CharField(max_length=50, blank=True, null=True, db_index=True),
        ),
        # Add composite indexes for better search performance
        migrations.AddIndex(
            model_name="trademark",
            index=models.Index(fields=["keyword", "status_label"], name="website_tra_keyword_idx"),
        ),
        migrations.AddIndex(
            model_name="trademark",
            index=models.Index(fields=["registration_number"], name="website_tra_reg_num_idx"),
        ),
        migrations.AddIndex(
            model_name="trademark",
            index=models.Index(fields=["serial_number"], name="website_tra_ser_num_idx"),
        ),
    ]
