from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils.timezone import is_aware

from website.models import SecurityIncident, SecurityIncidentHistory

User = get_user_model()


class SecurityIncidentModelTest(TestCase):
    """Test SecurityIncident model behavior"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.incident = SecurityIncident.objects.create(
            title="Test Incident",
            severity=SecurityIncident.Severity.HIGH,
            status=SecurityIncident.Status.OPEN,
            affected_systems="server1, server2",
            description="Test description",
            reporter=self.user,
        )

    def test_incident_creation(self):
        """Test that SecurityIncident is created correctly"""
        self.assertEqual(self.incident.title, "Test Incident")
        self.assertEqual(self.incident.severity, SecurityIncident.Severity.HIGH)
        self.assertEqual(self.incident.status, SecurityIncident.Status.OPEN)
        self.assertIsNotNone(self.incident.created_at)
        self.assertIsNone(self.incident.resolved_at)

    def test_incident_str_representation(self):
        """Test __str__ method returns expected format"""
        expected = "Test Incident (High) - Open"
        self.assertEqual(str(self.incident), expected)

    def test_resolved_at_auto_set_on_resolved(self):
        """Test that resolved_at is auto-set when status changes to RESOLVED"""
        self.assertIsNone(self.incident.resolved_at)

        self.incident.status = SecurityIncident.Status.RESOLVED
        self.incident.save()

        self.assertIsNotNone(self.incident.resolved_at)
        self.assertTrue(is_aware(self.incident.resolved_at))

    def test_resolved_at_cleared_on_reopen(self):
        """Test that resolved_at is cleared when reopening an incident"""
        # First resolve it
        self.incident.status = SecurityIncident.Status.RESOLVED
        self.incident.save()
        self.assertIsNotNone(self.incident.resolved_at)

        # Then reopen
        self.incident.status = SecurityIncident.Status.INVESTIGATING
        self.incident.save()

        self.assertIsNone(self.incident.resolved_at)

    def test_severity_choices(self):
        """Test all severity choices are valid"""
        severities = [
            SecurityIncident.Severity.LOW,
            SecurityIncident.Severity.MEDIUM,
            SecurityIncident.Severity.HIGH,
            SecurityIncident.Severity.CRITICAL,
        ]
        for severity in severities:
            incident = SecurityIncident.objects.create(
                title=f"Test {severity}", severity=severity, status=SecurityIncident.Status.OPEN, reporter=self.user
            )
            self.assertEqual(incident.severity, severity)

    def test_status_choices(self):
        """Test all status choices are valid"""
        statuses = [
            SecurityIncident.Status.OPEN,
            SecurityIncident.Status.INVESTIGATING,
            SecurityIncident.Status.RESOLVED,
        ]
        for status in statuses:
            incident = SecurityIncident.objects.create(
                title=f"Test {status}", severity=SecurityIncident.Severity.MEDIUM, status=status, reporter=self.user
            )
            self.assertEqual(incident.status, status)

    def test_ordering_by_created_at_desc(self):
        """Test that incidents are ordered by created_at descending"""
        incident2 = SecurityIncident.objects.create(
            title="Newer Incident",
            severity=SecurityIncident.Severity.LOW,
            status=SecurityIncident.Status.OPEN,
            reporter=self.user,
        )

        incidents = list(SecurityIncident.objects.all())
        self.assertEqual(incidents[0].id, incident2.id)
        self.assertEqual(incidents[1].id, self.incident.id)


class SecurityIncidentHistoryModelTest(TestCase):
    """Test SecurityIncidentHistory model behavior"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.incident = SecurityIncident.objects.create(
            title="Test Incident",
            severity=SecurityIncident.Severity.HIGH,
            status=SecurityIncident.Status.OPEN,
            reporter=self.user,
        )

    def test_history_creation(self):
        """Test that history records are created correctly"""
        history = SecurityIncidentHistory.objects.create(
            incident=self.incident, field_name="severity", old_value="MEDIUM", new_value="HIGH", changed_by=self.user
        )

        self.assertEqual(history.incident, self.incident)
        self.assertEqual(history.field_name, "severity")
        self.assertEqual(history.old_value, "MEDIUM")
        self.assertEqual(history.new_value, "HIGH")
        self.assertEqual(history.changed_by, self.user)
        self.assertIsNotNone(history.changed_at)

    def test_history_ordering_by_changed_at_desc(self):
        """Test that history records are ordered by changed_at descending"""
        history1 = SecurityIncidentHistory.objects.create(
            incident=self.incident,
            field_name="status",
            old_value="OPEN",
            new_value="INVESTIGATING",
            changed_by=self.user,
        )

        history2 = SecurityIncidentHistory.objects.create(
            incident=self.incident,
            field_name="status",
            old_value="INVESTIGATING",
            new_value="RESOLVED",
            changed_by=self.user,
        )

        histories = list(SecurityIncidentHistory.objects.all())
        self.assertEqual(histories[0].id, history2.id)
        self.assertEqual(histories[1].id, history1.id)

    def test_history_cascade_delete(self):
        """Test that history is deleted when incident is deleted"""
        SecurityIncidentHistory.objects.create(
            incident=self.incident, field_name="severity", old_value="LOW", new_value="HIGH", changed_by=self.user
        )

        incident_id = self.incident.id

        history_count = SecurityIncidentHistory.objects.filter(incident_id=incident_id).count()
        self.assertEqual(history_count, 1)

        # Delete the incident
        self.incident.delete()

        # History should also be deleted
        history_count = SecurityIncidentHistory.objects.filter(incident_id=incident_id).count()
        self.assertEqual(history_count, 0)
