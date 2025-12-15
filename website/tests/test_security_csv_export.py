from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from website.models import SecurityIncident
from website.views.security import _escape_csv_formula

User = get_user_model()


class CSVSanitizationTest(TestCase):
    """Test CSV formula injection mitigation"""

    def test_escape_leading_equals(self):
        """Test escaping leading = character"""
        result = _escape_csv_formula("=cmd")
        self.assertEqual(result, "'=cmd")

    def test_escape_leading_plus(self):
        """Test escaping leading + character"""
        result = _escape_csv_formula("+cmd")
        self.assertEqual(result, "'+cmd")

    def test_escape_leading_minus(self):
        """Test escaping leading - character"""
        result = _escape_csv_formula("-cmd")
        self.assertEqual(result, "'-cmd")

    def test_escape_leading_at(self):
        """Test escaping leading @ character"""
        result = _escape_csv_formula("@cmd")
        self.assertEqual(result, "'@cmd")

    def test_escape_leading_tab(self):
        """Test escaping leading tab character"""
        result = _escape_csv_formula("\tcmd")
        self.assertEqual(result, "cmd")

    def test_escape_leading_carriage_return(self):
        """Test escaping leading CR character"""
        result = _escape_csv_formula("\rcmd")
        self.assertEqual(result, "cmd")

    def test_escape_leading_line_feed(self):
        """Test escaping leading LF character"""
        result = _escape_csv_formula("\ncmd")
        self.assertEqual(result, "cmd")

    def test_whitespace_bypass_prevention(self):
        """Test that leading whitespace is stripped before checking"""
        result = _escape_csv_formula("  =cmd")
        self.assertEqual(result, "'=cmd")

    def test_safe_content_unchanged(self):
        """Test that safe content is not modified"""
        result = _escape_csv_formula("Safe content")
        self.assertEqual(result, "Safe content")

    def test_middle_formula_chars_unchanged(self):
        """Test that formula chars in middle are left unchanged (OWASP compliant)"""
        result = _escape_csv_formula("Safe=formula+here")
        self.assertEqual(result, "Safe=formula+here")

    def test_non_string_passthrough(self):
        """Test that non-string values pass through unchanged"""
        self.assertEqual(_escape_csv_formula(123), 123)
        self.assertEqual(_escape_csv_formula(None), None)

    def test_empty_string(self):
        """Test empty string handling"""
        result = _escape_csv_formula("")
        self.assertEqual(result, "")


class CSVExportTest(TestCase):
    """Test CSV export functionality"""

    def setUp(self):
        self.superuser = User.objects.create_superuser(
            username="admin", email="admin@example.com", password="testpass123"
        )
        self.staff_user = User.objects.create_user(
            username="staffuser", email="staff@example.com", password="testpass123", is_staff=True
        )

        SecurityIncident.objects.create(
            title="Test Incident",
            severity=SecurityIncident.Severity.HIGH,
            status=SecurityIncident.Status.OPEN,
            affected_systems="server1",
            reporter=self.superuser,
        )

    def tearDown(self):
        # Clear rate limit cache between tests
        cache.clear()

    def test_csv_export_requires_superuser(self):
        """Test that CSV export requires superuser"""
        self.client.login(username="staffuser", password="testpass123")
        response = self.client.get(reverse("security_dashboard"), {"export": "csv"})
        self.assertEqual(response.status_code, 403)

    def test_csv_export_accessible_by_superuser(self):
        """Test that superusers can export CSV"""
        self.client.login(username="admin", password="testpass123")
        response = self.client.get(reverse("security_dashboard"), {"export": "csv"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("attachment", response["Content-Disposition"])

    def test_csv_export_content(self):
        """Test CSV export content structure"""
        self.client.login(username="admin", password="testpass123")
        response = self.client.get(reverse("security_dashboard"), {"export": "csv"})

        content = response.content.decode("utf-8")
        self.assertIn("ID", content)  # Header
        self.assertIn("Title", content)
        self.assertIn("Severity", content)
        self.assertIn("Test Incident", content)  # Data

    def test_csv_export_escapes_dangerous_content(self):
        """Test that CSV export sanitizes formula injection attempts"""
        SecurityIncident.objects.create(
            title="=cmd|'/c calc'!A1",
            severity=SecurityIncident.Severity.CRITICAL,
            status=SecurityIncident.Status.OPEN,
            affected_systems="=SUM(A1:A10)",
            reporter=self.superuser,
        )

        self.client.login(username="admin", password="testpass123")
        response = self.client.get(reverse("security_dashboard"), {"export": "csv"})

        content = response.content.decode("utf-8")
        # Dangerous content should be escaped
        self.assertIn("'=cmd", content)
        self.assertIn("'=SUM", content)

    def test_csv_export_rate_limiting(self):
        """Test that CSV export is rate limited"""
        self.client.login(username="admin", password="testpass123")

        # Make multiple export requests
        for i in range(5):
            response = self.client.get(reverse("security_dashboard"), {"export": "csv"})
            self.assertEqual(response.status_code, 200)

        # 6th request should be rate limited
        response = self.client.get(reverse("security_dashboard"), {"export": "csv"})
        self.assertEqual(response.status_code, 429)  # Too Many Requests
        self.assertIn("rate limit", response.content.decode("utf-8").lower())
