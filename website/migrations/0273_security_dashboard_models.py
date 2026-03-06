from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("website", "0272_userprofile_leaderboard_score_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ── Organization-level security toggle ──────────────────────
        migrations.AddField(
            model_name="organization",
            name="security_monitoring_enabled",
            field=models.BooleanField(
                default=False,
                help_text="Enable security monitoring for this organization",
            ),
        ),
        # ── SecurityIncident org FK ─────────────────────────────────
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
        # ── UserLoginEvent ──────────────────────────────────────────
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
                "indexes": [
                    models.Index(
                        fields=["user", "-timestamp"],
                        name="login_user_ts_idx",
                    ),
                    models.Index(
                        fields=["event_type", "-timestamp"],
                        name="login_type_ts_idx",
                    ),
                    models.Index(
                        fields=["ip_address"],
                        name="login_ip_idx",
                    ),
                    models.Index(
                        fields=["organization", "-timestamp"],
                        name="login_org_ts_idx",
                    ),
                    models.Index(
                        fields=["organization", "event_type", "-timestamp"],
                        name="login_org_type_ts_idx",
                    ),
                ],
            },
        ),
        # ── UserBehaviorAnomaly ─────────────────────────────────────
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
                "indexes": [
                    models.Index(
                        fields=["user", "-created_at"],
                        name="anomaly_user_ts_idx",
                    ),
                    models.Index(
                        fields=["is_reviewed", "-created_at"],
                        name="anomaly_review_ts_idx",
                    ),
                    models.Index(
                        fields=["organization", "-created_at"],
                        name="anomaly_org_ts_idx",
                    ),
                ],
            },
        ),
        # ── ThreatIntelEntry ────────────────────────────────────────
        migrations.CreateModel(
            name="ThreatIntelEntry",
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
                ("title", models.CharField(max_length=255)),
                (
                    "threat_type",
                    models.CharField(
                        choices=[
                            ("malware", "Malware"),
                            ("phishing", "Phishing"),
                            ("ransomware", "Ransomware"),
                            ("data_breach", "Data Breach"),
                            ("ddos", "DDoS"),
                            ("insider_threat", "Insider Threat"),
                            ("zero_day", "Zero Day"),
                            ("other", "Other"),
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
                            ("critical", "Critical"),
                        ],
                        default="medium",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("active", "Active"),
                            ("mitigated", "Mitigated"),
                            ("expired", "Expired"),
                        ],
                        default="active",
                        max_length=20,
                    ),
                ),
                ("description", models.TextField(blank=True)),
                ("source", models.CharField(blank=True, max_length=255)),
                ("reference_url", models.URLField(blank=True, null=True)),
                ("indicators", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="threat_intel_entries",
                        to="website.organization",
                    ),
                ),
                (
                    "reported_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reported_threats",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "Threat intel entries",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["organization", "-created_at"],
                        name="threat_org_created_idx",
                    ),
                    models.Index(
                        fields=["threat_type"],
                        name="threat_type_idx",
                    ),
                    models.Index(
                        fields=["severity"],
                        name="threat_severity_idx",
                    ),
                    models.Index(
                        fields=["status"],
                        name="threat_status_idx",
                    ),
                ],
            },
        ),
        # ── Vulnerability ───────────────────────────────────────────
        migrations.CreateModel(
            name="Vulnerability",
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
                ("title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                (
                    "severity",
                    models.CharField(
                        choices=[
                            ("low", "Low"),
                            ("medium", "Medium"),
                            ("high", "High"),
                            ("critical", "Critical"),
                        ],
                        default="medium",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("open", "Open"),
                            ("in_progress", "In Progress"),
                            ("remediated", "Remediated"),
                            ("accepted_risk", "Accepted Risk"),
                            ("false_positive", "False Positive"),
                        ],
                        default="open",
                        max_length=20,
                    ),
                ),
                ("cve_id", models.CharField(blank=True, max_length=20)),
                (
                    "cvss_score",
                    models.DecimalField(
                        blank=True,
                        decimal_places=1,
                        max_digits=3,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.0")),
                            django.core.validators.MaxValueValidator(Decimal("10.0")),
                        ],
                    ),
                ),
                ("affected_component", models.CharField(blank=True, max_length=255)),
                ("remediation_steps", models.TextField(blank=True)),
                ("remediation_deadline", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("remediated_at", models.DateTimeField(blank=True, null=True)),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="vulnerabilities",
                        to="website.organization",
                    ),
                ),
                (
                    "issue",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="linked_vulnerabilities",
                        to="website.issue",
                    ),
                ),
                (
                    "assigned_to",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assigned_vulnerabilities",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "reported_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reported_vulnerabilities",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "Vulnerabilities",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(
                        fields=["organization", "-created_at"],
                        name="vuln_org_created_idx",
                    ),
                    models.Index(
                        fields=["severity"],
                        name="vuln_severity_idx",
                    ),
                    models.Index(
                        fields=["status"],
                        name="vuln_status_idx",
                    ),
                    models.Index(
                        fields=["organization", "status"],
                        name="vuln_org_status_idx",
                    ),
                ],
            },
        ),
        # ── ComplianceCheck ─────────────────────────────────────────
        migrations.CreateModel(
            name="ComplianceCheck",
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
                    "framework",
                    models.CharField(
                        choices=[
                            ("pci_dss", "PCI DSS"),
                            ("hipaa", "HIPAA"),
                            ("soc2", "SOC 2"),
                            ("gdpr", "GDPR"),
                            ("iso_27001", "ISO 27001"),
                            ("owasp_top10", "OWASP Top 10"),
                        ],
                        max_length=20,
                    ),
                ),
                ("requirement_id", models.CharField(max_length=50)),
                ("requirement_title", models.CharField(max_length=255)),
                ("description", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("compliant", "Compliant"),
                            ("non_compliant", "Non-Compliant"),
                            ("partial", "Partial"),
                            ("not_assessed", "Not Assessed"),
                        ],
                        default="not_assessed",
                        max_length=20,
                    ),
                ),
                ("evidence", models.TextField(blank=True)),
                ("last_assessed", models.DateTimeField(blank=True, null=True)),
                ("due_date", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "organization",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="compliance_checks",
                        to="website.organization",
                    ),
                ),
                (
                    "assessed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assessed_compliance_checks",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "Compliance checks",
                "ordering": ["framework", "requirement_id"],
                "indexes": [
                    models.Index(
                        fields=["organization", "framework"],
                        name="compliance_org_fw_idx",
                    ),
                    models.Index(
                        fields=["status"],
                        name="compliance_status_idx",
                    ),
                    models.Index(
                        fields=["organization", "status"],
                        name="compliance_org_status_idx",
                    ),
                ],
                "constraints": [
                    models.UniqueConstraint(
                        condition=models.Q(("organization__isnull", False)),
                        fields=["organization", "framework", "requirement_id"],
                        name="unique_compliance_with_org",
                    ),
                ],
            },
        ),
        # ── GeoIPCache ────────────────────────────────────────────
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
                "indexes": [
                    models.Index(fields=["country"], name="geoip_country_idx"),
                ],
            },
        ),
    ]
