from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from website.models import Organization, UserBehaviorAnomaly, UserLoginEvent
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

    def test_dismiss_anomaly_admin_only(self):
        anomaly = UserBehaviorAnomaly.objects.create(
            user=self.admin,
            organization=self.org,
            anomaly_type=UserBehaviorAnomaly.AnomalyType.NEW_IP,
            severity=UserBehaviorAnomaly.Severity.MEDIUM,
            description="Test anomaly",
        )
        # Manager cannot dismiss
        self.client.login(username="apimanager", password="testpass123")
        url = reverse("organization_security_api", args=[self.org.id])
        response = self.client.post(url, {"action": "dismiss_anomaly", "anomaly_id": anomaly.id})
        self.assertEqual(response.status_code, 403)

        # Admin can dismiss
        self.client.login(username="apiadmin", password="testpass123")
        response = self.client.post(url, {"action": "dismiss_anomaly", "anomaly_id": anomaly.id})
        self.assertEqual(response.status_code, 200)
        anomaly.refresh_from_db()
        self.assertTrue(anomaly.is_reviewed)

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
