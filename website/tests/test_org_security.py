from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from website.models import (
    ComplianceCheck,
    Organization,
    SecurityIncident,
    ThreatIntelEntry,
    UserBehaviorAnomaly,
    UserLoginEvent,
    Vulnerability,
)
from website.services.anomaly_detection import check_failed_login_anomalies, check_login_anomalies


class OrgSecurityModelTests(TestCase):
    """Test org FK on security models."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="secuser", password="testpass123")
        cls.org = Organization.objects.create(
            name="SecOrg",
            slug="sec-org",
            url="https://secorg.example.com",
            admin=cls.user,
            security_monitoring_enabled=True,
        )

    def test_login_event_with_org(self):
        event = UserLoginEvent.objects.create(
            user=self.user,
            organization=self.org,
            username_attempted="secuser",
            event_type=UserLoginEvent.EventType.LOGIN,
            ip_address="10.0.0.1",
        )
        self.assertEqual(event.organization, self.org)
        self.assertEqual(self.org.org_login_events.count(), 1)

    def test_login_event_without_org(self):
        event = UserLoginEvent.objects.create(
            user=self.user,
            username_attempted="secuser",
            event_type=UserLoginEvent.EventType.LOGIN,
        )
        self.assertIsNone(event.organization)

    def test_anomaly_with_org(self):
        anomaly = UserBehaviorAnomaly.objects.create(
            user=self.user,
            organization=self.org,
            anomaly_type=UserBehaviorAnomaly.AnomalyType.NEW_IP,
            severity=UserBehaviorAnomaly.Severity.MEDIUM,
            description="Test anomaly",
        )
        self.assertEqual(anomaly.organization, self.org)
        self.assertEqual(self.org.org_behavior_anomalies.count(), 1)

    def test_security_monitoring_enabled_default_false(self):
        org = Organization.objects.create(
            name="NoMonOrg",
            slug="no-mon-org",
            url="https://nomon.example.com",
        )
        self.assertFalse(org.security_monitoring_enabled)


class OrgScopedAnomalyDetectionTests(TestCase):
    """Test that anomaly detection respects org boundaries."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="anomuser", password="testpass123")
        cls.org_a = Organization.objects.create(
            name="OrgA",
            slug="org-a",
            url="https://orga.example.com",
            admin=cls.user,
            security_monitoring_enabled=True,
        )
        cls.org_b = Organization.objects.create(
            name="OrgB",
            slug="org-b",
            url="https://orgb.example.com",
            admin=cls.user,
            security_monitoring_enabled=True,
        )

    def test_new_ip_anomaly_scoped_to_org(self):
        """Anomaly detection for org A should not see org B events."""
        # Create prior login in org A from IP 10.0.0.1
        UserLoginEvent.objects.create(
            user=self.user,
            organization=self.org_a,
            username_attempted="anomuser",
            event_type=UserLoginEvent.EventType.LOGIN,
            ip_address="10.0.0.1",
        )
        # New login in org B from same IP should flag as new (no prior in org B)
        event_b = UserLoginEvent.objects.create(
            user=self.user,
            organization=self.org_b,
            username_attempted="anomuser",
            event_type=UserLoginEvent.EventType.LOGIN,
            ip_address="10.0.0.1",
        )
        check_login_anomalies(self.user, event_b, organization=self.org_b)
        # No anomaly because org B has no prior events (first login skipped)
        self.assertEqual(UserBehaviorAnomaly.objects.filter(organization=self.org_b).count(), 0)

    def test_anomaly_created_with_correct_org(self):
        """When anomaly is created, it should have the correct org FK."""
        # Create prior login so anomaly checks run
        UserLoginEvent.objects.create(
            user=self.user,
            organization=self.org_a,
            username_attempted="anomuser",
            event_type=UserLoginEvent.EventType.LOGIN,
            ip_address="10.0.0.1",
        )
        # New login from different IP
        event = UserLoginEvent.objects.create(
            user=self.user,
            organization=self.org_a,
            username_attempted="anomuser",
            event_type=UserLoginEvent.EventType.LOGIN,
            ip_address="10.0.0.2",
        )
        check_login_anomalies(self.user, event, organization=self.org_a)
        anomaly = UserBehaviorAnomaly.objects.filter(organization=self.org_a).first()
        self.assertIsNotNone(anomaly)
        self.assertEqual(anomaly.organization, self.org_a)

    def test_rapid_failures_scoped_to_org(self):
        """Rapid failure detection should be org-scoped."""
        # Create 5 failed events for org A
        for _ in range(5):
            event = UserLoginEvent.objects.create(
                user=self.user,
                organization=self.org_a,
                username_attempted="anomuser",
                event_type=UserLoginEvent.EventType.FAILED,
                ip_address="10.0.0.1",
            )
        check_failed_login_anomalies(self.user, event, organization=self.org_a)
        self.assertEqual(
            UserBehaviorAnomaly.objects.filter(
                organization=self.org_a,
                anomaly_type=UserBehaviorAnomaly.AnomalyType.RAPID_FAILURES,
            ).count(),
            1,
        )
        # Org B should have no rapid failure anomalies
        self.assertEqual(
            UserBehaviorAnomaly.objects.filter(
                organization=self.org_b,
                anomaly_type=UserBehaviorAnomaly.AnomalyType.RAPID_FAILURES,
            ).count(),
            0,
        )


class OrgSecurityDashboardViewTests(TestCase):
    """Test org security dashboard view access and data."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username="orgadmin", password="testpass123")
        self.manager = User.objects.create_user(username="orgmanager", password="testpass123")
        self.outsider = User.objects.create_user(username="outsider", password="testpass123")
        self.org = Organization.objects.create(
            name="DashOrg",
            slug="dash-org",
            url="https://dashorg.example.com",
            admin=self.admin,
            security_monitoring_enabled=True,
        )
        self.org.managers.add(self.manager)

    def test_unauthenticated_redirects_to_login(self):
        url = reverse("organization_security_dashboard", args=[self.org.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_outsider_denied(self):
        self.client.login(username="outsider", password="testpass123")
        url = reverse("organization_security_dashboard", args=[self.org.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)

    def test_admin_can_access(self):
        self.client.login(username="orgadmin", password="testpass123")
        url = reverse("organization_security_dashboard", args=[self.org.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Security Monitoring")

    def test_manager_can_access(self):
        self.client.login(username="orgmanager", password="testpass123")
        url = reverse("organization_security_dashboard", args=[self.org.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_monitoring_disabled_shows_prompt(self):
        self.org.security_monitoring_enabled = False
        self.org.save()
        self.client.login(username="orgadmin", password="testpass123")
        url = reverse("organization_security_dashboard", args=[self.org.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Security Monitoring is Disabled")

    def test_data_filtered_by_org(self):
        """Events from other orgs should not appear."""
        other_org = Organization.objects.create(
            name="OtherOrg",
            slug="other-org",
            url="https://other.example.com",
            admin=self.admin,
            security_monitoring_enabled=True,
        )
        # Create event in other org
        UserLoginEvent.objects.create(
            user=self.admin,
            organization=other_org,
            username_attempted="orgadmin",
            event_type=UserLoginEvent.EventType.LOGIN,
            ip_address="99.99.99.99",
        )
        # Create event in our org
        UserLoginEvent.objects.create(
            user=self.admin,
            organization=self.org,
            username_attempted="orgadmin",
            event_type=UserLoginEvent.EventType.LOGIN,
            ip_address="10.0.0.1",
        )
        self.client.login(username="orgadmin", password="testpass123")
        url = reverse("organization_security_dashboard", args=[self.org.id])
        response = self.client.get(url)
        self.assertContains(response, "10.0.0.1")
        self.assertNotContains(response, "99.99.99.99")

    def test_nonexistent_org_redirects(self):
        self.client.login(username="orgadmin", password="testpass123")
        url = reverse("organization_security_dashboard", args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)


class OrgSecurityApiViewTests(TestCase):
    """Test org security API endpoints."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username="apiadmin", password="testpass123")
        self.manager = User.objects.create_user(username="apimanager", password="testpass123")
        self.org = Organization.objects.create(
            name="ApiOrg",
            slug="api-org",
            url="https://apiorg.example.com",
            admin=self.admin,
            security_monitoring_enabled=True,
        )
        self.org.managers.add(self.manager)

    def test_get_events(self):
        self.client.login(username="apiadmin", password="testpass123")
        # Create event after login to avoid signal-created events affecting count
        UserLoginEvent.objects.filter(organization=self.org).delete()
        UserLoginEvent.objects.create(
            user=self.admin,
            organization=self.org,
            username_attempted="apiadmin",
            event_type=UserLoginEvent.EventType.LOGIN,
            ip_address="10.0.0.1",
        )
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.get(url, {"action": "events"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["events"]), 1)
        self.assertEqual(data["events"][0]["ip_address"], "10.0.0.1")

    def test_get_anomalies(self):
        UserBehaviorAnomaly.objects.create(
            user=self.admin,
            organization=self.org,
            anomaly_type=UserBehaviorAnomaly.AnomalyType.NEW_IP,
            severity=UserBehaviorAnomaly.Severity.MEDIUM,
            description="Test anomaly",
        )
        self.client.login(username="apiadmin", password="testpass123")
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.get(url, {"action": "anomalies"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["anomalies"]), 1)

    def test_dismiss_anomaly_admin_and_manager(self):
        anomaly = UserBehaviorAnomaly.objects.create(
            user=self.admin,
            organization=self.org,
            anomaly_type=UserBehaviorAnomaly.AnomalyType.NEW_IP,
            severity=UserBehaviorAnomaly.Severity.MEDIUM,
            description="Test anomaly",
        )
        # Manager can dismiss
        self.client.login(username="apimanager", password="testpass123")
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.post(url, {"action": "dismiss_anomaly", "anomaly_id": anomaly.id})
        self.assertEqual(response.status_code, 200)
        anomaly.refresh_from_db()
        self.assertTrue(anomaly.is_reviewed)

        # Admin can also dismiss
        anomaly2 = UserBehaviorAnomaly.objects.create(
            user=self.admin,
            organization=self.org,
            anomaly_type=UserBehaviorAnomaly.AnomalyType.NEW_IP,
            severity=UserBehaviorAnomaly.Severity.MEDIUM,
            description="Test anomaly 2",
        )
        self.client.login(username="apiadmin", password="testpass123")
        response = self.client.post(url, {"action": "dismiss_anomaly", "anomaly_id": anomaly2.id})
        self.assertEqual(response.status_code, 200)
        anomaly2.refresh_from_db()
        self.assertTrue(anomaly2.is_reviewed)

    def test_dismiss_anomaly_wrong_org(self):
        """Cannot dismiss anomaly from different org."""
        other_org = Organization.objects.create(
            name="Other",
            slug="other-sec",
            url="https://othersec.example.com",
            admin=self.admin,
        )
        anomaly = UserBehaviorAnomaly.objects.create(
            user=self.admin,
            organization=other_org,
            anomaly_type=UserBehaviorAnomaly.AnomalyType.NEW_IP,
            severity=UserBehaviorAnomaly.Severity.MEDIUM,
            description="Wrong org anomaly",
        )
        self.client.login(username="apiadmin", password="testpass123")
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.post(url, {"action": "dismiss_anomaly", "anomaly_id": anomaly.id})
        self.assertEqual(response.status_code, 404)

    def test_invalid_get_action(self):
        self.client.login(username="apiadmin", password="testpass123")
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.get(url, {"action": "invalid"})
        self.assertEqual(response.status_code, 400)

    def test_invalid_post_action(self):
        self.client.login(username="apiadmin", password="testpass123")
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.post(url, {"action": "invalid"})
        self.assertEqual(response.status_code, 400)

    def test_dismiss_anomaly_missing_id(self):
        self.client.login(username="apiadmin", password="testpass123")
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.post(url, {"action": "dismiss_anomaly"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("required", response.json()["error"])

    def test_dismiss_anomaly_invalid_id(self):
        self.client.login(username="apiadmin", password="testpass123")
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.post(url, {"action": "dismiss_anomaly", "anomaly_id": "abc"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid", response.json()["error"])


class OrgSignalTests(TestCase):
    """Test that signals create org-scoped events."""

    def setUp(self):
        self.user = User.objects.create_user(username="siguser", password="testpass123")
        self.org = Organization.objects.create(
            name="SigOrg",
            slug="sig-org",
            url="https://sigorg.example.com",
            admin=self.user,
            security_monitoring_enabled=True,
        )

    def test_login_creates_org_and_global_events(self):
        """Logging in should create both org-scoped and global events."""
        self.client = Client()
        self.client.login(username="siguser", password="testpass123")
        org_events = UserLoginEvent.objects.filter(user=self.user, organization=self.org).count()
        global_events = UserLoginEvent.objects.filter(user=self.user, organization__isnull=True).count()
        self.assertGreaterEqual(org_events, 1)
        self.assertGreaterEqual(global_events, 1)

    def test_login_no_org_events_when_monitoring_disabled(self):
        """If monitoring is disabled, no org-scoped events should be created."""
        self.org.security_monitoring_enabled = False
        self.org.save()
        self.client = Client()
        self.client.login(username="siguser", password="testpass123")
        org_events = UserLoginEvent.objects.filter(user=self.user, organization=self.org).count()
        self.assertEqual(org_events, 0)
        # Global event should still exist
        global_events = UserLoginEvent.objects.filter(user=self.user, organization__isnull=True).count()
        self.assertGreaterEqual(global_events, 1)

    def test_pii_anonymized_on_user_delete(self):
        """When a user is deleted, PII in login events should be anonymized (GDPR)."""
        UserLoginEvent.objects.create(
            user=self.user,
            organization=self.org,
            username_attempted="siguser",
            event_type=UserLoginEvent.EventType.LOGIN,
            ip_address="10.0.0.1",
            user_agent="Mozilla/5.0",
        )
        event_id = UserLoginEvent.objects.filter(user=self.user, organization=self.org).first().id
        self.user.delete()
        event = UserLoginEvent.objects.get(id=event_id)
        self.assertEqual(event.username_attempted, "[deleted]")
        self.assertIsNone(event.ip_address)
        self.assertEqual(event.user_agent, "")
        self.assertIsNone(event.user)


class OrgSecurityDashboardNewContextTests(TestCase):
    """Test new context variables added for big bold card redesign."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username="ctxadmin", password="testpass123")
        self.org = Organization.objects.create(
            name="CtxOrg",
            slug="ctx-org",
            url="https://ctxorg.example.com",
            admin=self.admin,
            security_monitoring_enabled=True,
        )

    def test_new_context_variables_present(self):
        """Dashboard should include all new context variables."""
        UserLoginEvent.objects.create(
            user=self.admin,
            organization=self.org,
            username_attempted="ctxadmin",
            event_type=UserLoginEvent.EventType.LOGIN,
            ip_address="10.0.0.1",
        )
        self.client.login(username="ctxadmin", password="testpass123")
        url = reverse("organization_security_dashboard", args=[self.org.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        ctx = response.context
        self.assertIn("login_success_rate", ctx)
        self.assertIn("peak_hour", ctx)
        self.assertIn("peak_hour_count", ctx)
        self.assertIn("most_active_users", ctx)
        self.assertIn("recent_incidents", ctx)
        self.assertIn("top_user_agents", ctx)
        self.assertIn("daily_failed_labels", ctx)
        self.assertIn("daily_failed_counts", ctx)
        self.assertIn("anomaly_reviewed_count", ctx)
        self.assertIn("anomaly_total_count", ctx)
        self.assertIn("anomaly_resolution_rate", ctx)

    def test_login_success_rate_calculation(self):
        """Success rate should be correctly computed from login and failed counts."""
        for _ in range(9):
            UserLoginEvent.objects.create(
                user=self.admin,
                organization=self.org,
                username_attempted="ctxadmin",
                event_type=UserLoginEvent.EventType.LOGIN,
                ip_address="10.0.0.1",
            )
        UserLoginEvent.objects.create(
            user=self.admin,
            organization=self.org,
            username_attempted="ctxadmin",
            event_type=UserLoginEvent.EventType.FAILED,
            ip_address="10.0.0.1",
        )
        self.client.login(username="ctxadmin", password="testpass123")
        url = reverse("organization_security_dashboard", args=[self.org.id])
        response = self.client.get(url)
        # 9 login + signal-created events vs 1 failed; rate should be > 0
        self.assertGreater(response.context["login_success_rate"], 0)

    def test_zero_logins_success_rate(self):
        """With no logins, success rate should be 0."""
        self.client.login(username="ctxadmin", password="testpass123")
        # Clear any signal-generated events
        UserLoginEvent.objects.filter(organization=self.org).delete()
        url = reverse("organization_security_dashboard", args=[self.org.id])
        response = self.client.get(url)
        self.assertEqual(response.context["login_success_rate"], 0)

    def test_anomaly_resolution_rate(self):
        """Resolution rate should reflect reviewed vs total anomalies."""
        UserBehaviorAnomaly.objects.create(
            user=self.admin,
            organization=self.org,
            anomaly_type=UserBehaviorAnomaly.AnomalyType.NEW_IP,
            severity=UserBehaviorAnomaly.Severity.MEDIUM,
            description="Test 1",
            is_reviewed=True,
        )
        UserBehaviorAnomaly.objects.create(
            user=self.admin,
            organization=self.org,
            anomaly_type=UserBehaviorAnomaly.AnomalyType.NEW_IP,
            severity=UserBehaviorAnomaly.Severity.LOW,
            description="Test 2",
            is_reviewed=False,
        )
        self.client.login(username="ctxadmin", password="testpass123")
        url = reverse("organization_security_dashboard", args=[self.org.id])
        response = self.client.get(url)
        self.assertEqual(response.context["anomaly_resolution_rate"], 50)
        self.assertEqual(response.context["anomaly_reviewed_count"], 1)
        self.assertEqual(response.context["anomaly_total_count"], 2)

    def test_recent_incidents_in_context(self):
        """Recent incidents should be populated."""
        SecurityIncident.objects.create(
            title="Test Incident",
            organization=self.org,
            severity=SecurityIncident.Severity.HIGH,
            status=SecurityIncident.Status.OPEN,
        )
        self.client.login(username="ctxadmin", password="testpass123")
        url = reverse("organization_security_dashboard", args=[self.org.id])
        response = self.client.get(url)
        self.assertEqual(len(response.context["recent_incidents"]), 1)

    def test_daily_failed_labels_length(self):
        """Daily failed labels should always have 7 entries."""
        self.client.login(username="ctxadmin", password="testpass123")
        url = reverse("organization_security_dashboard", args=[self.org.id])
        response = self.client.get(url)
        self.assertEqual(len(response.context["daily_failed_labels"]), 7)
        self.assertEqual(len(response.context["daily_failed_counts"]), 7)


class OrgSecurityApiNewActionsTests(TestCase):
    """Test new API drill-down actions."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username="apinewadmin", password="testpass123")
        self.org = Organization.objects.create(
            name="ApiNewOrg",
            slug="api-new-org",
            url="https://apinew.example.com",
            admin=self.admin,
            security_monitoring_enabled=True,
        )

    def test_user_events_action(self):
        """user_events action should return events for a specific user."""
        UserLoginEvent.objects.create(
            user=self.admin,
            organization=self.org,
            username_attempted="apinewadmin",
            event_type=UserLoginEvent.EventType.LOGIN,
            ip_address="10.0.0.1",
        )
        self.client.login(username="apinewadmin", password="testpass123")
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.get(url, {"action": "user_events", "username": "apinewadmin"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("events", data)
        self.assertGreaterEqual(len(data["events"]), 1)

    def test_user_events_missing_username(self):
        """user_events without username should return 400."""
        self.client.login(username="apinewadmin", password="testpass123")
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.get(url, {"action": "user_events"})
        self.assertEqual(response.status_code, 400)

    def test_ip_events_action(self):
        """ip_events action should return events from a specific IP."""
        UserLoginEvent.objects.create(
            user=self.admin,
            organization=self.org,
            username_attempted="apinewadmin",
            event_type=UserLoginEvent.EventType.LOGIN,
            ip_address="192.168.1.1",
        )
        self.client.login(username="apinewadmin", password="testpass123")
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.get(url, {"action": "ip_events", "ip": "192.168.1.1"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("events", data)
        self.assertGreaterEqual(len(data["events"]), 1)

    def test_ip_events_missing_ip(self):
        """ip_events without ip should return 400."""
        self.client.login(username="apinewadmin", password="testpass123")
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.get(url, {"action": "ip_events"})
        self.assertEqual(response.status_code, 400)

    def test_incidents_action(self):
        """incidents action should return paginated incidents."""
        SecurityIncident.objects.create(
            title="Incident 1",
            organization=self.org,
            severity=SecurityIncident.Severity.HIGH,
        )
        self.client.login(username="apinewadmin", password="testpass123")
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.get(url, {"action": "incidents"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("incidents", data)
        self.assertIn("total", data)
        self.assertEqual(data["total"], 1)

    def test_incidents_action_empty(self):
        """incidents action with no incidents should return empty list."""
        self.client.login(username="apinewadmin", password="testpass123")
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.get(url, {"action": "incidents"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["incidents"]), 0)
        self.assertEqual(data["total"], 0)

    def test_incidents_invalid_page(self):
        """incidents action with invalid page should default to page 1."""
        self.client.login(username="apinewadmin", password="testpass123")
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.get(url, {"action": "incidents", "page": "abc"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["page"], 1)


class ThreatIntelModelTests(TestCase):
    """Test ThreatIntelEntry model."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="threatuser", password="testpass123")
        cls.org = Organization.objects.create(
            name="ThreatOrg",
            slug="threat-org",
            url="https://threatorg.example.com",
            admin=cls.user,
            security_monitoring_enabled=True,
        )

    def test_create_threat_with_org(self):
        threat = ThreatIntelEntry.objects.create(
            organization=self.org,
            title="Phishing Campaign",
            threat_type=ThreatIntelEntry.ThreatType.PHISHING,
            severity=ThreatIntelEntry.Severity.HIGH,
            source="Internal",
        )
        self.assertEqual(threat.organization, self.org)
        self.assertEqual(threat.status, "active")
        self.assertEqual(self.org.threat_intel_entries.count(), 1)

    def test_create_threat_without_org(self):
        threat = ThreatIntelEntry.objects.create(
            title="Global Malware",
            threat_type=ThreatIntelEntry.ThreatType.MALWARE,
        )
        self.assertIsNone(threat.organization)

    def test_threat_str(self):
        threat = ThreatIntelEntry.objects.create(
            title="Test Threat",
            threat_type=ThreatIntelEntry.ThreatType.RANSOMWARE,
            severity=ThreatIntelEntry.Severity.CRITICAL,
        )
        self.assertIn("Test Threat", str(threat))
        self.assertIn("Ransomware", str(threat))


class VulnerabilityModelTests(TestCase):
    """Test Vulnerability model."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="vulnuser", password="testpass123")
        cls.org = Organization.objects.create(
            name="VulnOrg",
            slug="vuln-org",
            url="https://vulnorg.example.com",
            admin=cls.user,
            security_monitoring_enabled=True,
        )

    def test_create_vulnerability(self):
        vuln = Vulnerability.objects.create(
            organization=self.org,
            title="SQL Injection",
            severity=Vulnerability.Severity.CRITICAL,
            cve_id="CVE-2025-1234",
            cvss_score=Decimal("9.8"),
        )
        self.assertEqual(vuln.organization, self.org)
        self.assertEqual(vuln.status, "open")
        self.assertIsNone(vuln.remediated_at)

    def test_auto_remediated_at_on_status_change(self):
        vuln = Vulnerability.objects.create(
            organization=self.org,
            title="XSS Bug",
            severity=Vulnerability.Severity.HIGH,
        )
        self.assertIsNone(vuln.remediated_at)
        vuln.status = Vulnerability.Status.REMEDIATED
        vuln.save()
        vuln.refresh_from_db()
        self.assertIsNotNone(vuln.remediated_at)

    def test_remediated_at_cleared_on_reopen(self):
        vuln = Vulnerability.objects.create(
            organization=self.org,
            title="Reopen Test",
            severity=Vulnerability.Severity.MEDIUM,
            status=Vulnerability.Status.REMEDIATED,
        )
        self.assertIsNotNone(vuln.remediated_at)
        vuln.status = Vulnerability.Status.OPEN
        vuln.save()
        vuln.refresh_from_db()
        self.assertIsNone(vuln.remediated_at)


class ComplianceCheckModelTests(TestCase):
    """Test ComplianceCheck model."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="compuser", password="testpass123")
        cls.org = Organization.objects.create(
            name="CompOrg",
            slug="comp-org",
            url="https://comporg.example.com",
            admin=cls.user,
            security_monitoring_enabled=True,
        )

    def test_create_compliance_check(self):
        check = ComplianceCheck.objects.create(
            organization=self.org,
            framework=ComplianceCheck.Framework.PCI_DSS,
            requirement_id="PCI 3.4",
            requirement_title="Render PAN unreadable",
            status=ComplianceCheck.Status.COMPLIANT,
        )
        self.assertEqual(check.organization, self.org)
        self.assertEqual(check.get_framework_display(), "PCI DSS")

    def test_unique_together_constraint(self):
        ComplianceCheck.objects.create(
            organization=self.org,
            framework=ComplianceCheck.Framework.GDPR,
            requirement_id="Art. 17",
            requirement_title="Right to erasure",
        )
        with self.assertRaises(IntegrityError):
            ComplianceCheck.objects.create(
                organization=self.org,
                framework=ComplianceCheck.Framework.GDPR,
                requirement_id="Art. 17",
                requirement_title="Duplicate",
            )

    def test_compliance_str(self):
        check = ComplianceCheck.objects.create(
            organization=self.org,
            framework=ComplianceCheck.Framework.SOC2,
            requirement_id="CC6.1",
            requirement_title="Logical access",
        )
        self.assertIn("SOC 2", str(check))
        self.assertIn("CC6.1", str(check))


class NewDashboardContextTests(TestCase):
    """Test new context variables for expanded dashboard components."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username="newctxadmin", password="testpass123")
        self.org = Organization.objects.create(
            name="NewCtxOrg",
            slug="new-ctx-org",
            url="https://newctxorg.example.com",
            admin=self.admin,
            security_monitoring_enabled=True,
        )

    def test_threat_context_present(self):
        ThreatIntelEntry.objects.create(
            organization=self.org,
            title="Test Threat",
            threat_type=ThreatIntelEntry.ThreatType.MALWARE,
        )
        self.client.login(username="newctxadmin", password="testpass123")
        url = reverse("organization_security_dashboard", args=[self.org.id])
        response = self.client.get(url)
        ctx = response.context
        self.assertIn("active_threats_count", ctx)
        self.assertIn("total_threats_count", ctx)
        self.assertIn("threat_type_labels", ctx)
        self.assertIn("recent_threats", ctx)
        self.assertEqual(ctx["total_threats_count"], 1)
        self.assertEqual(ctx["active_threats_count"], 1)

    def test_vulnerability_context_present(self):
        Vulnerability.objects.create(
            organization=self.org,
            title="Test Vuln",
            severity=Vulnerability.Severity.HIGH,
        )
        self.client.login(username="newctxadmin", password="testpass123")
        url = reverse("organization_security_dashboard", args=[self.org.id])
        response = self.client.get(url)
        ctx = response.context
        self.assertIn("vuln_total", ctx)
        self.assertIn("vuln_open", ctx)
        self.assertIn("vuln_severity_labels", ctx)
        self.assertEqual(ctx["vuln_total"], 1)
        self.assertEqual(ctx["vuln_open"], 1)

    def test_compliance_context_present(self):
        ComplianceCheck.objects.create(
            organization=self.org,
            framework=ComplianceCheck.Framework.PCI_DSS,
            requirement_id="PCI 1.1",
            requirement_title="Firewall config",
            status=ComplianceCheck.Status.COMPLIANT,
        )
        ComplianceCheck.objects.create(
            organization=self.org,
            framework=ComplianceCheck.Framework.PCI_DSS,
            requirement_id="PCI 1.2",
            requirement_title="DMZ config",
            status=ComplianceCheck.Status.NON_COMPLIANT,
        )
        self.client.login(username="newctxadmin", password="testpass123")
        url = reverse("organization_security_dashboard", args=[self.org.id])
        response = self.client.get(url)
        ctx = response.context
        self.assertIn("framework_summaries", ctx)
        self.assertIn("overall_compliance_pct", ctx)
        self.assertEqual(ctx["overall_compliance_pct"], 50)
        self.assertEqual(len(ctx["framework_summaries"]), 1)
        self.assertEqual(ctx["framework_summaries"][0]["label"], "PCI DSS")

    def test_network_traffic_context_present(self):
        self.client.login(username="newctxadmin", password="testpass123")
        url = reverse("organization_security_dashboard", args=[self.org.id])
        response = self.client.get(url)
        ctx = response.context
        self.assertIn("ip_diversity_labels", ctx)
        self.assertIn("ip_diversity_counts", ctx)
        self.assertIn("daily_traffic_labels", ctx)
        self.assertIn("daily_traffic_counts", ctx)
        self.assertIn("top_subnets", ctx)
        self.assertIn("failed_ip_origins", ctx)
        self.assertEqual(len(ctx["ip_diversity_labels"]), 7)

    def test_incidents_summary_context_present(self):
        SecurityIncident.objects.create(
            title="Resolved Inc",
            organization=self.org,
            severity=SecurityIncident.Severity.HIGH,
            status=SecurityIncident.Status.RESOLVED,
        )
        self.client.login(username="newctxadmin", password="testpass123")
        url = reverse("organization_security_dashboard", args=[self.org.id])
        response = self.client.get(url)
        ctx = response.context
        self.assertIn("monthly_incident_labels", ctx)
        self.assertIn("monthly_incident_totals", ctx)
        self.assertIn("affected_systems_labels", ctx)
        self.assertIn("mttr_hours", ctx)

    def test_empty_state_zero_counts(self):
        """All new component counts should be zero with no data."""
        self.client.login(username="newctxadmin", password="testpass123")
        url = reverse("organization_security_dashboard", args=[self.org.id])
        response = self.client.get(url)
        ctx = response.context
        self.assertEqual(ctx["active_threats_count"], 0)
        self.assertEqual(ctx["total_threats_count"], 0)
        self.assertEqual(ctx["vuln_total"], 0)
        self.assertEqual(ctx["vuln_overdue"], 0)
        self.assertEqual(ctx["overall_compliance_pct"], 0)
        self.assertEqual(ctx["mttr_hours"], 0)

    def test_vuln_overdue_count(self):
        """Vulns past deadline should be counted as overdue."""
        Vulnerability.objects.create(
            organization=self.org,
            title="Overdue Vuln",
            severity=Vulnerability.Severity.HIGH,
            status=Vulnerability.Status.OPEN,
            remediation_deadline=timezone.now().date() - timedelta(days=5),
        )
        Vulnerability.objects.create(
            organization=self.org,
            title="On Time Vuln",
            severity=Vulnerability.Severity.MEDIUM,
            status=Vulnerability.Status.OPEN,
            remediation_deadline=timezone.now().date() + timedelta(days=30),
        )
        self.client.login(username="newctxadmin", password="testpass123")
        url = reverse("organization_security_dashboard", args=[self.org.id])
        response = self.client.get(url)
        self.assertEqual(response.context["vuln_overdue"], 1)

    def test_mttr_calculation(self):
        """MTTR should be computed from resolved incidents."""
        now = timezone.now()
        inc = SecurityIncident.objects.create(
            title="Resolved Quick",
            organization=self.org,
            severity=SecurityIncident.Severity.MEDIUM,
            status=SecurityIncident.Status.RESOLVED,
        )
        # Force created_at to 24h ago using queryset update
        SecurityIncident.objects.filter(id=inc.id).update(created_at=now - timedelta(hours=24))
        inc.refresh_from_db()
        self.client.login(username="newctxadmin", password="testpass123")
        url = reverse("organization_security_dashboard", args=[self.org.id])
        response = self.client.get(url)
        self.assertGreater(response.context["mttr_hours"], 0)


class NewApiActionTests(TestCase):
    """Test new API actions for threats, vulnerabilities, and compliance."""

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(username="newapiadmin", password="testpass123")
        self.manager = User.objects.create_user(username="newapimanager", password="testpass123")
        self.outsider = User.objects.create_user(username="newapioutsider", password="testpass123")
        self.org = Organization.objects.create(
            name="NewApiOrg",
            slug="new-api-org",
            url="https://newapiorg.example.com",
            admin=self.admin,
            security_monitoring_enabled=True,
        )
        self.org.managers.add(self.manager)

    def test_get_threats(self):
        ThreatIntelEntry.objects.create(
            organization=self.org,
            title="API Threat",
            threat_type=ThreatIntelEntry.ThreatType.PHISHING,
        )
        self.client.login(username="newapiadmin", password="testpass123")
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.get(url, {"action": "threats"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("threats", data)
        self.assertEqual(len(data["threats"]), 1)
        self.assertEqual(data["threats"][0]["title"], "API Threat")

    def test_get_vulnerabilities(self):
        Vulnerability.objects.create(
            organization=self.org,
            title="API Vuln",
            severity=Vulnerability.Severity.HIGH,
            cve_id="CVE-2025-9999",
        )
        self.client.login(username="newapiadmin", password="testpass123")
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.get(url, {"action": "vulnerabilities"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("vulnerabilities", data)
        self.assertEqual(len(data["vulnerabilities"]), 1)
        self.assertEqual(data["vulnerabilities"][0]["cve_id"], "CVE-2025-9999")

    def test_get_compliance(self):
        ComplianceCheck.objects.create(
            organization=self.org,
            framework=ComplianceCheck.Framework.GDPR,
            requirement_id="Art. 5",
            requirement_title="Data minimization",
            status=ComplianceCheck.Status.COMPLIANT,
        )
        self.client.login(username="newapiadmin", password="testpass123")
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.get(url, {"action": "compliance"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("compliance", data)
        self.assertEqual(len(data["compliance"]), 1)

    def test_get_compliance_with_framework_filter(self):
        ComplianceCheck.objects.create(
            organization=self.org,
            framework=ComplianceCheck.Framework.GDPR,
            requirement_id="Art. 5",
            requirement_title="Data minimization",
        )
        ComplianceCheck.objects.create(
            organization=self.org,
            framework=ComplianceCheck.Framework.SOC2,
            requirement_id="CC1.1",
            requirement_title="Control environment",
        )
        self.client.login(username="newapiadmin", password="testpass123")
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.get(url, {"action": "compliance", "framework": "gdpr"})
        data = response.json()
        self.assertEqual(len(data["compliance"]), 1)
        self.assertEqual(data["compliance"][0]["framework"], "GDPR")

    def test_update_vuln_status(self):
        vuln = Vulnerability.objects.create(
            organization=self.org,
            title="To Remediate",
            severity=Vulnerability.Severity.HIGH,
        )
        self.client.login(username="newapiadmin", password="testpass123")
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.post(
            url,
            {
                "action": "update_vuln_status",
                "vuln_id": vuln.id,
                "status": "remediated",
            },
        )
        self.assertEqual(response.status_code, 200)
        vuln.refresh_from_db()
        self.assertEqual(vuln.status, "remediated")
        self.assertIsNotNone(vuln.remediated_at)

    def test_update_vuln_status_forbidden_for_outsider(self):
        vuln = Vulnerability.objects.create(
            organization=self.org,
            title="Forbidden Vuln",
            severity=Vulnerability.Severity.LOW,
        )
        self.client.login(username="newapioutsider", password="testpass123")
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.post(
            url,
            {
                "action": "update_vuln_status",
                "vuln_id": vuln.id,
                "status": "remediated",
            },
        )
        # outsider should be redirected by validate_organization_user
        self.assertIn(response.status_code, [302, 403])

    def test_update_vuln_status_invalid_status(self):
        vuln = Vulnerability.objects.create(
            organization=self.org,
            title="Invalid Status",
            severity=Vulnerability.Severity.LOW,
        )
        self.client.login(username="newapiadmin", password="testpass123")
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.post(
            url,
            {
                "action": "update_vuln_status",
                "vuln_id": vuln.id,
                "status": "nonexistent",
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_update_compliance_status(self):
        check = ComplianceCheck.objects.create(
            organization=self.org,
            framework=ComplianceCheck.Framework.HIPAA,
            requirement_id="164.312",
            requirement_title="Access controls",
            status=ComplianceCheck.Status.NOT_ASSESSED,
        )
        self.client.login(username="newapimanager", password="testpass123")
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.post(
            url,
            {
                "action": "update_compliance_status",
                "check_id": check.id,
                "status": "compliant",
            },
        )
        self.assertEqual(response.status_code, 200)
        check.refresh_from_db()
        self.assertEqual(check.status, "compliant")
        self.assertIsNotNone(check.last_assessed)
        self.assertEqual(check.assessed_by, self.manager)

    def test_update_compliance_status_invalid_status(self):
        check = ComplianceCheck.objects.create(
            organization=self.org,
            framework=ComplianceCheck.Framework.HIPAA,
            requirement_id="164.313",
            requirement_title="Audit controls",
        )
        self.client.login(username="newapiadmin", password="testpass123")
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.post(
            url,
            {
                "action": "update_compliance_status",
                "check_id": check.id,
                "status": "invalid",
            },
        )
        self.assertEqual(response.status_code, 400)
