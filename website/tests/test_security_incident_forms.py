from django.test import TestCase

from website.models import SecurityIncident
from website.security_incident_form import SecurityIncidentForm


class SecurityIncidentFormTest(TestCase):
    """Test SecurityIncidentForm validation and cleaning"""

    def test_form_valid_data(self):
        """Test form with valid data"""
        data = {
            "title": "Test Incident",
            "severity": SecurityIncident.Severity.HIGH,
            "status": SecurityIncident.Status.OPEN,
            "affected_systems": "server1, server2",
            "description": "Test description",
        }
        form = SecurityIncidentForm(data=data)
        self.assertTrue(form.is_valid())

    def test_form_missing_required_fields(self):
        """Test form validation with missing required fields"""
        data = {
            "severity": SecurityIncident.Severity.HIGH,
            # Missing title
        }
        form = SecurityIncidentForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_clean_affected_systems_strips_whitespace(self):
        """Test that affected_systems cleaning strips whitespace"""
        data = {
            "title": "Test",
            "severity": SecurityIncident.Severity.MEDIUM,
            "status": SecurityIncident.Status.OPEN,
            "affected_systems": "  server1, server2  ",
            "description": "Test",
        }
        form = SecurityIncidentForm(data=data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["affected_systems"], "server1, server2")

    def test_form_all_fields_present(self):
        """Test that form includes all expected fields"""
        form = SecurityIncidentForm()
        expected_fields = ["title", "severity", "status", "affected_systems", "description"]
        for field in expected_fields:
            self.assertIn(field, form.fields)
