import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0268_userloginevent_userbehavioranomaly"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
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
                on_delete=django.db.models.deletion.SET_NULL,
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
        migrations.AlterModelOptions(
            name="userbehavioranomaly",
            options={"ordering": ["-created_at"], "verbose_name_plural": "User behavior anomalies"},
        ),
        migrations.AlterField(
            model_name="userbehavioranomaly",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="behavior_anomalies",
                to=settings.AUTH_USER_MODEL,
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
            model_name="userloginevent",
            index=models.Index(
                fields=["organization", "event_type", "-timestamp"],
                name="login_org_type_ts_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="userbehavioranomaly",
            index=models.Index(
                fields=["organization", "-created_at"],
                name="anomaly_org_ts_idx",
            ),
        ),
        migrations.AddField(
            model_name="userbehavioranomaly",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="userbehavioranomaly",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reviewed_anomalies",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
