from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.test import TestCase
from django.urls import reverse

from website.models import Issue, SecurityIncident, SecurityIncidentHistory

User = get_user_model()


class CustomFilterTest(TestCase):
    """Test custom template filters"""

    def test_replace_filter_for_field_names(self):
        template = Template('{% load custom_filters %}{{ "resolved_at"|replace:"_| " }}')
        rendered = template.render(Context({}))

        self.assertEqual(rendered, "resolved at")


class SecurityDashboardViewTest(TestCase):
    """Test SecurityDashboardView"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.staff_user = User.objects.create_user(
            username="staffuser", email="staff@example.com", password="testpass123", is_staff=True
        )
        self.superuser = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="testpass123"
        )

        # Create test incidents
        SecurityIncident.objects.create(
            title="Critical Security Issue",
            severity=SecurityIncident.Severity.CRITICAL,
            status=SecurityIncident.Status.OPEN,
            reporter=self.staff_user,
        )
        SecurityIncident.objects.create(
            title="Minor Issue",
            severity=SecurityIncident.Severity.LOW,
            status=SecurityIncident.Status.RESOLVED,
            reporter=self.staff_user,
        )

    def test_dashboard_includes_related_security_issues(self):
        """Test that dashboard includes related security issues with label=4"""
        self.client.login(username="staffuser", password="testpass123")

        Issue.objects.create(
            description="Test issue",
            label=4,
        )

        response = self.client.get(reverse("security_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("security_issues", response.context)
        self.assertEqual(len(response.context["security_issues"]), 1)

    def test_dashboard_requires_authentication(self):
        """Test that dashboard requires login"""
        response = self.client.get(reverse("security_dashboard"))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_dashboard_requires_staff(self):
        """Test that regular users cannot access dashboard"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("security_dashboard"))
        self.assertEqual(response.status_code, 403)  # Forbidden

    def test_dashboard_accessible_by_staff(self):
        """Test that staff users can access dashboard"""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("security_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Critical Security Issue")

    def test_dashboard_accessible_by_superuser(self):
        """Test that superusers can access dashboard"""
        self.client.login(username="admin", password="testpass123")
        response = self.client.get(reverse("security_dashboard"))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_filter_by_severity(self):
        """Test filtering incidents by severity"""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("security_dashboard"), {"severity": "critical"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Critical Security Issue")
        self.assertNotContains(response, "Minor Issue")

    def test_dashboard_filter_by_status(self):
        """Test filtering incidents by status"""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("security_dashboard"), {"status": "resolved"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Minor Issue")
        self.assertNotContains(response, "Critical Security Issue")

    def test_dashboard_context_data(self):
        """Test that dashboard provides expected context"""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("security_dashboard"))

        self.assertIn("incidents", response.context)
        self.assertIn("severity_breakdown", response.context)
        self.assertIn("status_breakdown", response.context)
        self.assertIn("incident_count", response.context)

        self.assertEqual(response.context["incident_count"], 2)


class SecurityIncidentCreateViewTest(TestCase):
    """Test SecurityIncidentCreateView"""

    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="staffuser", email="staff@example.com", password="testpass123", is_staff=True
        )
        self.regular_user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )

    def test_create_requires_staff(self):
        """Test that only staff can create incidents"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("security_incident_add"))
        self.assertEqual(response.status_code, 403)

    def test_create_view_accessible_by_staff(self):
        """Test that staff can access create view"""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("security_incident_add"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Create Security Incident")

    def test_create_incident_success(self):
        """Test successful incident creation"""
        self.client.login(username="staffuser", password="testpass123")
        data = {
            "title": "New Security Incident",
            "severity": SecurityIncident.Severity.HIGH,
            "status": SecurityIncident.Status.OPEN,
            "affected_systems": "server1, database",
            "description": "Test incident",
        }
        response = self.client.post(reverse("security_incident_add"), data)

        self.assertEqual(response.status_code, 302)  # Redirect on success
        self.assertEqual(SecurityIncident.objects.count(), 1)

        incident = SecurityIncident.objects.first()
        self.assertEqual(incident.title, "New Security Incident")
        self.assertEqual(incident.reporter, self.staff_user)


class SecurityIncidentUpdateViewTest(TestCase):
    """Test SecurityIncidentUpdateView with history tracking"""

    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="staffuser", email="staff@example.com", password="testpass123", is_staff=True
        )
        self.incident = SecurityIncident.objects.create(
            title="Original Title",
            severity=SecurityIncident.Severity.MEDIUM,
            status=SecurityIncident.Status.OPEN,
            affected_systems="server1",
            description="Original description",
            reporter=self.staff_user,
        )

    def test_update_creates_history_record(self):
        """Test that updating an incident creates history records"""
        self.client.login(username="staffuser", password="testpass123")

        data = {
            "title": "Updated Title",
            "severity": SecurityIncident.Severity.HIGH,
            "status": SecurityIncident.Status.INVESTIGATING,
            "affected_systems": "server1, server2",
            "description": "Updated description",
        }
        response = self.client.post(reverse("security_incident_edit", kwargs={"pk": self.incident.pk}), data)

        self.assertEqual(response.status_code, 302)

        # Check history records were created
        histories = SecurityIncidentHistory.objects.filter(incident=self.incident)
        self.assertGreater(histories.count(), 0)

        # Verify specific field changes
        title_history = histories.filter(field_name="title").first()
        self.assertIsNotNone(title_history)
        self.assertEqual(title_history.old_value, "Original Title")
        self.assertEqual(title_history.new_value, "Updated Title")
        self.assertEqual(title_history.changed_by, self.staff_user)

    def test_update_unchanged_fields_no_history(self):
        """Test that unchanged fields don't create history records"""
        self.client.login(username="staffuser", password="testpass123")

        # Update only title
        data = {
            "title": "Updated Title",
            "severity": self.incident.severity,  # Unchanged
            "status": self.incident.status,  # Unchanged
            "affected_systems": self.incident.affected_systems,  # Unchanged
            "description": self.incident.description,  # Unchanged
        }
        response = self.client.post(reverse("security_incident_edit", kwargs={"pk": self.incident.pk}), data)

        # Only one history record (for title)
        histories = SecurityIncidentHistory.objects.filter(incident=self.incident)
        self.assertEqual(histories.count(), 1)
        self.assertEqual(histories.first().field_name, "title")


class SecurityIncidentDetailViewTest(TestCase):
    """Test SecurityIncidentDetailView"""

    def setUp(self):
        self.staff_user = User.objects.create_user(
            username="staffuser", email="staff@example.com", password="testpass123", is_staff=True
        )
        self.incident = SecurityIncident.objects.create(
            title="Test Incident",
            severity=SecurityIncident.Severity.HIGH,
            status=SecurityIncident.Status.OPEN,
            reporter=self.staff_user,
        )

        # Create history
        SecurityIncidentHistory.objects.create(
            incident=self.incident,
            field_name="severity",
            old_value="medium",
            new_value="high",
            changed_by=self.staff_user,
        )

    def test_detail_view_shows_incident(self):
        """Test that detail view displays incident information"""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("security_incident_detail", kwargs={"pk": self.incident.pk}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Incident")
        self.assertContains(response, "high")

    def test_detail_view_shows_history(self):
        """Test that detail view includes history context"""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("security_incident_detail", kwargs={"pk": self.incident.pk}))

        self.assertIn("history_entries", response.context)
        self.assertIn("history_count", response.context)
        self.assertEqual(response.context["history_count"], 1)
