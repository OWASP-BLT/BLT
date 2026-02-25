import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0270_githubcomment"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Organization-level security toggle
        migrations.AddField(
            model_name="organization",
            name="security_monitoring_enabled",
            field=models.BooleanField(
                default=False,
                help_text="Enable security monitoring for this organization",
            ),
        ),
        # SecurityIncident org FK
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
        migrations.AddIndex(
            model_name="securityincident",
            index=models.Index(
                fields=["organization", "-created_at"],
                name="incident_org_created_idx",
            ),
        ),
        # UserLoginEvent with org FK included
        migrations.CreateModel(
            name="UserLoginEvent",
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
                ("username_attempted", models.CharField(max_length=150)),
                (
                    "event_type",
                    models.CharField(
                        choices=[
                            ("login", "Login"),
                            ("logout", "Logout"),
                            ("failed", "Failed Login"),
                        ],
                        max_length=10,
                    ),
                ),
                (
                    "ip_address",
                    models.GenericIPAddressField(blank=True, null=True),
                ),
                ("user_agent", models.TextField(blank=True, default="")),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="login_events",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="org_login_events",
                        to="website.organization",
                    ),
                ),
            ],
            options={
                "ordering": ["-timestamp"],
            },
        ),
        migrations.AddIndex(
            model_name="userloginevent",
            index=models.Index(fields=["user", "-timestamp"], name="login_user_ts_idx"),
        ),
        migrations.AddIndex(
            model_name="userloginevent",
            index=models.Index(fields=["event_type", "-timestamp"], name="login_type_ts_idx"),
        ),
        migrations.AddIndex(
            model_name="userloginevent",
            index=models.Index(fields=["ip_address"], name="login_ip_idx"),
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
        # UserBehaviorAnomaly with org FK, SET_NULL user, reviewed_at/by included
        migrations.CreateModel(
            name="UserBehaviorAnomaly",
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
                    "anomaly_type",
                    models.CharField(
                        choices=[
                            ("new_ip", "New IP Address"),
                            ("new_ua", "New User Agent"),
                            ("unusual_time", "Unusual Login Time"),
                            ("rapid_failures", "Rapid Failed Logins"),
                        ],
                        max_length=20,
                    ),
                ),
                (
                    "severity",
                    models.CharField(
                        choices=[
                            ("low", "Low"),
                            ("medium", "Medium"),
                            ("high", "High"),
                        ],
                        max_length=10,
                    ),
                ),
                ("description", models.TextField()),
                ("details", models.JSONField(blank=True, default=dict)),
                ("is_reviewed", models.BooleanField(default=False)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "login_event",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="anomalies",
                        to="website.userloginevent",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="behavior_anomalies",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="org_behavior_anomalies",
                        to="website.organization",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviewed_anomalies",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
                "verbose_name_plural": "User behavior anomalies",
            },
        ),
        migrations.AddIndex(
            model_name="userbehavioranomaly",
            index=models.Index(fields=["user", "-created_at"], name="anomaly_user_ts_idx"),
        ),
        migrations.AddIndex(
            model_name="userbehavioranomaly",
            index=models.Index(
                fields=["is_reviewed", "-created_at"],
                name="anomaly_review_ts_idx",
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
