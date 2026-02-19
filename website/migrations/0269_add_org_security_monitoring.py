import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0268_userloginevent_userbehavioranomaly"),
    ]

    operations = [
        migrations.AddField(
            model_name="organization",
            name="security_monitoring_enabled",
            field=models.BooleanField(
                default=False,
                help_text="Enable security monitoring for this organization",
            ),
        ),
        migrations.AddField(
            model_name="securityincident",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="security_incidents",
                to="website.organization",
            ),
        ),
        migrations.AddField(
            model_name="userloginevent",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="org_login_events",
                to="website.organization",
            ),
        ),
        migrations.AddField(
            model_name="userbehavioranomaly",
            name="organization",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="org_behavior_anomalies",
                to="website.organization",
            ),
        ),
        migrations.AddIndex(
            model_name="securityincident",
            index=models.Index(
                fields=["organization", "-created_at"],
                name="incident_org_created_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="userloginevent",
            index=models.Index(
                fields=["organization", "-timestamp"],
                name="login_org_ts_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="userbehavioranomaly",
            index=models.Index(
                fields=["organization", "-created_at"],
                name="anomaly_org_ts_idx",
            ),
        ),
    ]
