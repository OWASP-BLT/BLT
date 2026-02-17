from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from website.models import UserBehaviorAnomaly, UserLoginEvent
from website.services.anomaly_detection import check_failed_login_anomalies, check_login_anomalies


class UserLoginEventModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="testuser", password="testpass123")

    def test_create_login_event(self):
        event = UserLoginEvent.objects.create(
            user=self.user,
            username_attempted="testuser",
            event_type=UserLoginEvent.EventType.LOGIN,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )
        self.assertEqual(event.event_type, "login")
        self.assertEqual(event.ip_address, "192.168.1.1")

    def test_nullable_user_for_failed_login(self):
        event = UserLoginEvent.objects.create(
            user=None,
            username_attempted="nonexistent",
            event_type=UserLoginEvent.EventType.FAILED,
        )
        self.assertIsNone(event.user)
        self.assertEqual(event.username_attempted, "nonexistent")

    def test_str_representation(self):
        event = UserLoginEvent.objects.create(
            user=self.user,
            username_attempted="testuser",
            event_type=UserLoginEvent.EventType.LOGIN,
        )
        self.assertIn("testuser", str(event))
        self.assertIn("Login", str(event))

    def test_ordering_newest_first(self):
        e1 = UserLoginEvent.objects.create(
            user=self.user,
            username_attempted="testuser",
            event_type=UserLoginEvent.EventType.LOGIN,
        )
        e2 = UserLoginEvent.objects.create(
            user=self.user,
            username_attempted="testuser",
            event_type=UserLoginEvent.EventType.LOGOUT,
        )
        events = list(UserLoginEvent.objects.all())
        self.assertEqual(events[0].pk, e2.pk)
        self.assertEqual(events[1].pk, e1.pk)


class UserBehaviorAnomalyModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="anomalyuser", password="testpass123")

    def test_create_anomaly_with_json_details(self):
        anomaly = UserBehaviorAnomaly.objects.create(
            user=self.user,
            anomaly_type=UserBehaviorAnomaly.AnomalyType.NEW_IP,
            severity=UserBehaviorAnomaly.Severity.MEDIUM,
            description="Login from new IP",
            details={"new_ip": "10.0.0.1", "known_ips": ["192.168.1.1"]},
        )
        self.assertEqual(anomaly.details["new_ip"], "10.0.0.1")
        self.assertFalse(anomaly.is_reviewed)

    def test_str_representation(self):
        anomaly = UserBehaviorAnomaly.objects.create(
            user=self.user,
            anomaly_type=UserBehaviorAnomaly.AnomalyType.RAPID_FAILURES,
            severity=UserBehaviorAnomaly.Severity.HIGH,
            description="Many failures",
        )
        result = str(anomaly)
        self.assertIn("Rapid Failed Logins", result)
        self.assertIn("High", result)


class SignalHandlerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="signaluser", password="testpass123")
        self.factory = RequestFactory()

    def test_login_creates_event(self):
        self.client.login(username="signaluser", password="testpass123")
        events = UserLoginEvent.objects.filter(user=self.user, event_type=UserLoginEvent.EventType.LOGIN)
        self.assertTrue(events.exists())

    def test_logout_creates_event(self):
        self.client.login(username="signaluser", password="testpass123")
        self.client.logout()
        events = UserLoginEvent.objects.filter(user=self.user, event_type=UserLoginEvent.EventType.LOGOUT)
        self.assertTrue(events.exists())

    def test_failed_login_creates_event(self):
        self.client.login(username="signaluser", password="wrongpassword")
        events = UserLoginEvent.objects.filter(
            username_attempted="signaluser",
            event_type=UserLoginEvent.EventType.FAILED,
        )
        self.assertTrue(events.exists())

    def test_ip_captured_on_login(self):
        # Call the signal handler directly with a real request to test IP extraction.
        # client.login() creates a bare HttpRequest without REMOTE_ADDR.
        from website.user_activity_signals import on_user_logged_in

        request = self.factory.get("/")
        request.META["REMOTE_ADDR"] = "192.168.1.50"
        on_user_logged_in(sender=self.user.__class__, request=request, user=self.user)

        event = UserLoginEvent.objects.filter(user=self.user, event_type=UserLoginEvent.EventType.LOGIN).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.ip_address, "192.168.1.50")


class AnomalyDetectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="detectuser", password="testpass123")

    def _create_login_event(self, ip="192.168.1.1", ua="OldBrowser/1.0", **kwargs):
        return UserLoginEvent.objects.create(
            user=self.user,
            username_attempted="detectuser",
            event_type=UserLoginEvent.EventType.LOGIN,
            ip_address=ip,
            user_agent=ua,
            **kwargs,
        )

    def test_new_ip_detected(self):
        # Create prior history
        self._create_login_event(ip="192.168.1.1")
        # New login from different IP
        new_event = self._create_login_event(ip="10.0.0.5")
        check_login_anomalies(self.user, new_event)

        anomalies = UserBehaviorAnomaly.objects.filter(
            user=self.user,
            anomaly_type=UserBehaviorAnomaly.AnomalyType.NEW_IP,
        )
        self.assertTrue(anomalies.exists())
        self.assertEqual(anomalies.first().severity, "medium")

    def test_no_false_positive_on_first_login(self):
        # First ever login should NOT trigger anomaly
        event = self._create_login_event(ip="192.168.1.1")
        check_login_anomalies(self.user, event)

        anomalies = UserBehaviorAnomaly.objects.filter(user=self.user)
        self.assertFalse(anomalies.exists())

    def test_new_user_agent_detected(self):
        self._create_login_event(ua="OldBrowser/1.0")
        new_event = self._create_login_event(ua="NewBrowser/2.0")
        check_login_anomalies(self.user, new_event)

        anomalies = UserBehaviorAnomaly.objects.filter(
            user=self.user,
            anomaly_type=UserBehaviorAnomaly.AnomalyType.NEW_UA,
        )
        self.assertTrue(anomalies.exists())
        self.assertEqual(anomalies.first().severity, "low")

    def test_unusual_time_detected(self):
        self._create_login_event()
        unusual_event = self._create_login_event()
        # auto_now_add fields can't be overridden via .save(); use queryset update
        forced_time = unusual_event.timestamp.replace(hour=3)
        UserLoginEvent.objects.filter(pk=unusual_event.pk).update(timestamp=forced_time)
        unusual_event.refresh_from_db()

        check_login_anomalies(self.user, unusual_event)

        anomalies = UserBehaviorAnomaly.objects.filter(
            user=self.user,
            anomaly_type=UserBehaviorAnomaly.AnomalyType.UNUSUAL_TIME,
        )
        self.assertTrue(anomalies.exists())

    @override_settings(ANOMALY_RAPID_FAILURE_COUNT=3)
    def test_rapid_failures_detected(self):
        # Create 3 rapid failures
        for _ in range(3):
            UserLoginEvent.objects.create(
                user=self.user,
                username_attempted="detectuser",
                event_type=UserLoginEvent.EventType.FAILED,
                ip_address="192.168.1.1",
            )

        last_event = UserLoginEvent.objects.filter(
            user=self.user,
            event_type=UserLoginEvent.EventType.FAILED,
        ).first()

        check_failed_login_anomalies(self.user, last_event)

        anomalies = UserBehaviorAnomaly.objects.filter(
            user=self.user,
            anomaly_type=UserBehaviorAnomaly.AnomalyType.RAPID_FAILURES,
        )
        self.assertTrue(anomalies.exists())
        self.assertEqual(anomalies.first().severity, "high")

    @override_settings(ANOMALY_RAPID_FAILURE_COUNT=3)
    def test_rapid_failures_deduplication(self):
        for _ in range(3):
            UserLoginEvent.objects.create(
                user=self.user,
                username_attempted="detectuser",
                event_type=UserLoginEvent.EventType.FAILED,
                ip_address="192.168.1.1",
            )

        last_event = UserLoginEvent.objects.filter(user=self.user, event_type=UserLoginEvent.EventType.FAILED).first()

        # Call twice
        check_failed_login_anomalies(self.user, last_event)
        check_failed_login_anomalies(self.user, last_event)

        anomalies = UserBehaviorAnomaly.objects.filter(
            user=self.user,
            anomaly_type=UserBehaviorAnomaly.AnomalyType.RAPID_FAILURES,
        )
        self.assertEqual(anomalies.count(), 1)


class SecurityDashboardUserActivityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.staff_user = User.objects.create_user(username="staffuser", password="testpass123", is_staff=True)
        cls.superuser = User.objects.create_user(
            username="superuser", password="testpass123", is_staff=True, is_superuser=True
        )
        cls.normal_user = User.objects.create_user(username="normaluser", password="testpass123")

    def test_non_staff_denied_dashboard(self):
        self.client.login(username="normaluser", password="testpass123")
        response = self.client.get(reverse("security_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_staff_can_access_dashboard(self):
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("security_dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_context_has_activity_data(self):
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("security_dashboard"))
        self.assertIn("recent_login_events", response.context)
        self.assertIn("anomaly_count", response.context)
        self.assertIn("login_success_count", response.context)
        self.assertIn("login_failed_count", response.context)
        self.assertIn("hourly_login_data", response.context)
        self.assertIn("anomaly_chart_data", response.context)

    def test_api_returns_json_events(self):
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("security_user_activity_api"), {"action": "events"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("events", data)

    def test_api_returns_json_anomalies(self):
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("security_user_activity_api"), {"action": "anomalies"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("anomalies", data)

    def test_api_denies_non_staff(self):
        self.client.login(username="normaluser", password="testpass123")
        response = self.client.get(reverse("security_user_activity_api"), {"action": "events"})
        self.assertEqual(response.status_code, 403)

    def test_api_invalid_action(self):
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("security_user_activity_api"), {"action": "invalid"})
        self.assertEqual(response.status_code, 400)

    def test_dismiss_anomaly_requires_superuser(self):
        anomaly = UserBehaviorAnomaly.objects.create(
            user=self.staff_user,
            anomaly_type=UserBehaviorAnomaly.AnomalyType.NEW_IP,
            severity=UserBehaviorAnomaly.Severity.MEDIUM,
            description="Test anomaly",
        )

        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(
            reverse("security_user_activity_api"),
            {"action": "dismiss_anomaly", "id": anomaly.id},
        )
        self.assertEqual(response.status_code, 403)

    def test_superuser_can_dismiss_anomaly(self):
        anomaly = UserBehaviorAnomaly.objects.create(
            user=self.staff_user,
            anomaly_type=UserBehaviorAnomaly.AnomalyType.NEW_IP,
            severity=UserBehaviorAnomaly.Severity.MEDIUM,
            description="Test anomaly",
        )

        self.client.login(username="superuser", password="testpass123")
        response = self.client.get(
            reverse("security_user_activity_api"),
            {"action": "dismiss_anomaly", "id": anomaly.id},
        )
        self.assertEqual(response.status_code, 200)
        anomaly.refresh_from_db()
        self.assertTrue(anomaly.is_reviewed)
