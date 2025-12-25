from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from website.models import SecurityIncident

User = get_user_model()


class SecurityIncidentAPITest(TestCase):
    """Test SecurityIncidentViewSet API"""

    def setUp(self):
        self.client = APIClient()

        self.regular_user = User.objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.staff_user = User.objects.create_user(
            username="staffuser", email="staff@example.com", password="testpass123", is_staff=True
        )
        self.superuser = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="testpass123"
        )

        self.incident = SecurityIncident.objects.create(
            title="API Test Incident",
            severity=SecurityIncident.Severity.HIGH,
            status=SecurityIncident.Status.OPEN,
            reporter=self.staff_user,
        )

    def test_api_requires_authentication(self):
        """Test that API endpoints require authentication"""
        response = self.client.get("/api/v1/security-incidents/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)  # Unauthorized

    def test_api_requires_admin(self):
        """Test that regular users cannot access API"""
        self.client.force_authenticate(user=self.regular_user)
        response = self.client.get("/api/v1/security-incidents/")
        self.assertEqual(response.status_code, 403)  # Forbidden

    def test_api_list_accessible_by_staff(self):
        """Test that staff users can list incidents via API"""
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get("/api/v1/security-incidents/")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        results = payload["results"]

        self.assertIn("results", payload)
        self.assertIsInstance(results, list)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["title"], "API Test Incident")

    def test_api_retrieve_incident(self):
        """Test retrieving a specific incident"""
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get(f"/api/v1/security-incidents/{self.incident.id}/")

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["title"], "API Test Incident")
        self.assertEqual(data["severity"], "high")

    def test_api_filter_by_severity(self):
        """Test filtering incidents by severity"""
        # Create another incident with different severity
        SecurityIncident.objects.create(
            title="Low Severity Incident",
            severity=SecurityIncident.Severity.LOW,
            status=SecurityIncident.Status.OPEN,
            reporter=self.staff_user,
        )

        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get("/api/v1/security-incidents/?severity=high")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        results = payload["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["severity"], "high")

    def test_api_filter_by_status(self):
        """Test filtering incidents by status"""
        # Create resolved incident
        SecurityIncident.objects.create(
            title="Resolved Incident",
            severity=SecurityIncident.Severity.MEDIUM,
            status=SecurityIncident.Status.RESOLVED,
            reporter=self.staff_user,
        )

        self.client.force_authenticate(user=self.staff_user)
        response = self.client.get("/api/v1/security-incidents/?status=resolved")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        results = payload["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "resolved")

    def test_api_create_incident(self):
        """Test creating an incident via API"""
        self.client.force_authenticate(user=self.staff_user)
        data = {
            "title": "API Created Incident",
            "severity": "critical",
            "status": "open",
            "affected_systems": "api-server",
            "description": "Created via API",
        }
        response = self.client.post("/api/v1/security-incidents/", data)

        self.assertEqual(response.status_code, 201)
        self.assertEqual(SecurityIncident.objects.count(), 2)

        new_incident = SecurityIncident.objects.get(title="API Created Incident")
        self.assertEqual(new_incident.severity, SecurityIncident.Severity.CRITICAL)

    def test_api_update_incident(self):
        """Test updating an incident via API"""
        self.client.force_authenticate(user=self.staff_user)
        data = {
            "title": "Updated Title",
            "severity": "critical",
            "status": "investigating",
            "affected_systems": "server1, server2",
            "description": "Updated via API",
        }
        response = self.client.put(f"/api/v1/security-incidents/{self.incident.id}/", data)

        self.assertEqual(response.status_code, 200)
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.title, "Updated Title")
        self.assertEqual(self.incident.severity, SecurityIncident.Severity.CRITICAL)

    def test_api_delete_incident(self):
        """Test deleting an incident via API"""
        self.client.force_authenticate(user=self.staff_user)
        response = self.client.delete(f"/api/v1/security-incidents/{self.incident.id}/")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(SecurityIncident.objects.count(), 0)
