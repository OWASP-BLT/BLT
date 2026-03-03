from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0272_security_dashboard_models"),
    ]

    operations = [
        migrations.CreateModel(
            name="GeoIPCache",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "ip_address",
                    models.GenericIPAddressField(db_index=True, unique=True),
                ),
                ("latitude", models.FloatField(blank=True, null=True)),
                ("longitude", models.FloatField(blank=True, null=True)),
                ("city", models.CharField(blank=True, max_length=100)),
                ("country", models.CharField(blank=True, max_length=100)),
                ("country_code", models.CharField(blank=True, max_length=10)),
                ("isp", models.CharField(blank=True, max_length=255)),
                ("resolved_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "verbose_name": "GeoIP cache entry",
                "verbose_name_plural": "GeoIP cache entries",
            },
        ),
        migrations.AddIndex(
            model_name="geoipcache",
            index=models.Index(fields=["country"], name="geoip_country_idx"),
        ),
    ]
