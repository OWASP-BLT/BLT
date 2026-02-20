from io import BytesIO
from unittest.mock import Mock, patch

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.transaction import atomic
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_str
from rest_framework import status
from rest_framework.test import APITestCase

from website.models import Organization, Project, Repo
from website.utils import rebuild_safe_url, validate_file_type


class FileValidationTest(APITestCase):
    def test_valid_png(self):
        """Test a valid PNG file."""
        file_content = b"fake png content"
        file = InMemoryUploadedFile(
            file=BytesIO(file_content),
            field_name="thumbnail",
            name="test.png",
            content_type="image/png",
            size=len(file_content),
            charset=None,
        )
        request = Mock()
        request.FILES = {"thumbnail": file}
        is_valid, error_message = validate_file_type(request, "thumbnail", allowed_extensions=["png"])
        self.assertTrue(is_valid, "Validation should pass for a valid PNG file")
        self.assertIsNone(error_message, "Error message should be None for a valid file")

    def test_invalid_extension(self):
        """Test a file with an invalid extension."""
        file_content = b"fake pdf content"
        file = InMemoryUploadedFile(
            file=BytesIO(file_content),
            field_name="thumbnail",
            name="test.pdf",
            content_type="application/pdf",
            size=len(file_content),
            charset=None,
        )
        request = Mock()
        request.FILES = {"thumbnail": file}
        is_valid, error_message = validate_file_type(request, "thumbnail", allowed_extensions=["png"])
        self.assertFalse(is_valid, "Validation should fail for an invalid extension")
        self.assertIsNotNone(error_message, "Error message should be set for an invalid file")

    def test_no_file(self):
        """Test when no file is provided."""
        request = Mock()
        request.FILES = {}
        is_valid, error_message = validate_file_type(request, "thumbnail", allowed_extensions=["png"])
        self.assertTrue(is_valid, "Validation should pass when no file is provided")
        self.assertIsNone(error_message, "Error message should be None when no file is provided")


class RebuildSafeUrlTestCase(TestCase):
    @patch("socket.getaddrinfo")
    def test_rebuild_safe_url(self, mock_getaddrinfo):
        # Mock DNS resolution to return a valid public IP address for example.com
        # This simulates successful DNS resolution to a public IP (not private/loopback/reserved)
        # Format: [(family, type, proto, canonname, sockaddr)]
        mock_getaddrinfo.return_value = [
            (2, 1, 6, "", ("93.184.216.34", 0))  # IPv4 address for example.com
        ]

        test_cases = [
            # Test case with credentials and encoded control characters in the path.
            (
                "https://user:pass@example.com/%0a:%0dsome-path?query=test#ekdes",
                "https://example.com/%250a%3A%250dsome-path",
            ),
            # Test case with multiple slashes in the path.
            ("https://example.com//multiple///slashes", "https://example.com/multiple/slashes"),
            # Test case with no modifications needed.
            ("https://example.com/normal/path", "https://example.com/normal/path"),
            # Test with CRLF characters.
            ("https://example.com/%0d%0a", "https://example.com/%250d%250a"),
            # Test with path traversal.
            ("https://example.com/../../test", "https://example.com/test"),
        ]

        for input_url, expected in test_cases:
            with self.subTest(url=input_url):
                result = rebuild_safe_url(input_url)
                self.assertEqual(result, expected)


class APITests(APITestCase):
    register_url = "/auth/registration/"
    login_url = "/auth/login/"
    password_reset_url = "/auth/password/reset/"

    USERNAME = "person"
    PASS = "Gassword123&&"
    NEW_PASS = "Gasswoasdfas2234"
    EMAIL = "person1@world.com"

    REGISTRATION_DATA = {
        "username": USERNAME,
        "password1": PASS,
        "password2": PASS,
        "email": EMAIL,
    }

    def _generate_uid_and_token(self, user):
        result = {}

        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        result["uid"] = urlsafe_base64_encode(force_bytes(user.pk))
        result["token"] = default_token_generator.make_token(user)
        return result

    def test_login_by_email(self):
        payload = {
            "username": self.USERNAME.lower(),
            "password": self.PASS,
        }

        user = get_user_model().objects.create_user(self.USERNAME, self.EMAIL, self.PASS)

        # Verify the email
        EmailAddress.objects.create(user=user, email=self.EMAIL, verified=True, primary=True)

        response = self.client.post(self.login_url, data=payload, status_code=200)
        self.assertEqual("key" in response.json().keys(), True)
        self.token = response.json()["key"]

        payload = {
            "username": self.USERNAME.lower(),
            "password": self.PASS,
        }
        response = self.client.post(self.login_url, data=payload)
        self.assertEqual("key" in response.json().keys(), True)
        self.token = response.json()["key"]

    def test_registration(self):
        user_count = get_user_model().objects.all().count()
        result = self.client.post(self.register_url, data=self.REGISTRATION_DATA, status_code=201)

        # Since email verification is required, we need to verify the email
        self.assertEqual(get_user_model().objects.all().count(), user_count + 1)
        new_user = get_user_model().objects.latest("id")
        self.assertEqual(new_user.username, self.REGISTRATION_DATA["username"])

        # Check that we got the verification email message
        self.assertIn("detail", result.data)
        self.assertEqual(result.data["detail"], "Verification e-mail sent.")

        # Verify the email
        email_address = EmailAddress.objects.get(user=new_user, email=self.EMAIL)
        email_address.verified = True
        email_address.save()

        # Now try to login to get the key
        login_payload = {
            "username": self.USERNAME.lower(),
            "password": self.PASS,
        }
        login_response = self.client.post(self.login_url, data=login_payload)
        self.assertIn("key", login_response.data)

    def test_create_issue(self):
        @atomic
        def create_issue():
            url = "/api/v1/issues/"
            with open("website/static/img/background.png", "rb") as _file:
                data = {
                    "url": "http://www.google.com",
                    "description": "test",
                    "screenshot": _file,
                    "label": "0",
                    "token": "test",
                    "type": "test",
                }
                response = self.client.post(url, data, format="multipart")
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        return create_issue

    def test_password_reset(self):
        user = get_user_model().objects.create_user(self.USERNAME, self.EMAIL, self.PASS)

        mail_count = len(mail.outbox)
        payload = {"email": self.EMAIL}
        self.client.post(self.password_reset_url, data=payload, status_code=200)
        self.assertEqual(len(mail.outbox), mail_count + 1)

        url_kwargs = self._generate_uid_and_token(user)
        url = reverse("rest_password_reset_confirm")

        data = {
            "new_password1": self.NEW_PASS,
            "new_password2": self.NEW_PASS,
            "uid": force_str(url_kwargs["uid"]),
            "token": url_kwargs["token"],
        }
        url = reverse("rest_password_reset_confirm")
        self.client.post(url, data=data, status_code=200)
        for item in mail.outbox:
            print(item.__dict__)

    def test_get_bug_hunt(self):
        url = "/api/v1/hunt/?"
        response = self.client.get("".join([url, "activeHunt=1/"]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if len(response.data):
            self.assertTrue(
                response.data[0]["starts_on"] < timezone.now() and response.data[0]["end_on"] > timezone.now(),
                "Invalid Response",
            )
        response = self.client.get("".join([url, "previousHunt=1/"]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if len(response.data):
            self.assertLess(response.data[0]["end_on"], timezone.now(), "Invalid Response")
        response = self.client.get("".join([url, "upcomingHunt=1/"]))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if len(response.data):
            self.assertGreater(response.data[0]["starts_on"], timezone.now(), "Invalid Response")

    def test_get_issues(self):
        url = "/api/v1/issues/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if len(response.data):
            count = response.data["count"]
            for n in range(0, count):
                message = "Test is failed"
                self.assertTrue(response.data["results"][n].is_hidden, message)

    def test_get_userissues(self):
        url = "/api/v1/userissues/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if len(response.data):
            count = response.data["count"]
            for n in range(0, count):
                message = "Test is failed"
                self.assertTrue(response.data["results"][n].is_hidden, message)


class TestPasswordResetUnknownEmail(APITestCase):
    """Test password reset behavior for unknown email addresses"""

    password_reset_url = "/auth/password/reset/"

    def test_password_reset_unknown_email_no_email_sent(self):
        """Test password reset with unknown email - should not send email"""
        # Clear the mail outbox
        mail.outbox = []

        # Try to reset password for non-existent email
        response = self.client.post(self.password_reset_url, {"email": "nonexistent@example.com"})

        print("\nTest: Password reset for unknown email")
        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.json() if response.status_code == 200 else response.content}")
        print(f"Emails sent: {len(mail.outbox)}")

        # The response should be 200 OK to not reveal account existence
        self.assertEqual(response.status_code, 200)

        # But NO email should actually be sent for non-existent accounts
        self.assertEqual(len(mail.outbox), 0, "No email should be sent for unknown accounts")

        print("✓ Correct: No email sent for unknown account")
        print("✓ Response still returns 200 OK (doesn't leak account existence)")

    def test_password_reset_known_email_sends_email(self):
        """Test password reset with known email - should send email"""
        # Create a user
        user = get_user_model().objects.create_user(
            username="testuser", email="testuser@example.com", password="testpass123"
        )

        # Clear the mail outbox
        mail.outbox = []

        # Try to reset password for existing email
        response = self.client.post(self.password_reset_url, {"email": "testuser@example.com"})

        print("\nTest: Password reset for known email")
        print(f"Response status: {response.status_code}")
        print(f"Response data: {response.json() if response.status_code == 200 else response.content}")
        print(f"Emails sent: {len(mail.outbox)}")

        # The response should be 200 OK
        self.assertEqual(response.status_code, 200)

        # Email SHOULD be sent for existing accounts
        self.assertEqual(len(mail.outbox), 1, "Email should be sent for known accounts")

        print("✓ Correct: Email sent for known account")


class ProjectFreshnessFilteringTestCase(APITestCase):
    """Test cases for Project API freshness filtering"""

    def setUp(self):
        """Set up test data"""
        self.org = Organization.objects.create(name="Test Organization", url="https://test.org")

        # Create projects with different freshness scores
        self.high_freshness_project = Project.objects.create(
            name="High Freshness", organization=self.org, url="https://github.com/test/high", freshness=85.50
        )

        self.medium_freshness_project = Project.objects.create(
            name="Medium Freshness", organization=self.org, url="https://github.com/test/medium", freshness=50.25
        )

        self.low_freshness_project = Project.objects.create(
            name="Low Freshness", organization=self.org, url="https://github.com/test/low", freshness=15.75
        )

        self.zero_freshness_project = Project.objects.create(
            name="Zero Freshness", organization=self.org, url="https://github.com/test/zero", freshness=0.0
        )

    def test_filter_by_min_freshness_threshold(self):
        """Test filtering projects by valid freshness threshold"""
        response = self.client.get("/api/v1/projects/?freshness=50")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Should return projects with freshness >= 50
        self.assertEqual(len(data["results"]), 2)
        names = [p["name"] for p in data["results"]]
        self.assertIn("High Freshness", names)
        self.assertIn("Medium Freshness", names)

    def test_filter_by_high_freshness(self):
        """Test filtering with high freshness threshold"""
        response = self.client.get("/api/v1/projects/?freshness=80")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Only high freshness project should match
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["name"], "High Freshness")

    def test_filter_freshness_invalid_negative(self):
        """Test that negative freshness values are rejected"""
        response = self.client.get("/api/v1/projects/?freshness=-10")

        self.assertEqual(response.status_code, 400)
        self.assertIn("must be between 0 and 100", response.json()["error"])

    def test_filter_freshness_invalid_over_100(self):
        """Test that freshness values over 100 are rejected"""
        response = self.client.get("/api/v1/projects/?freshness=150")

        self.assertEqual(response.status_code, 400)
        self.assertIn("must be between 0 and 100", response.json()["error"])

    def test_filter_freshness_invalid_non_numeric(self):
        """Test that non-numeric freshness values are rejected"""
        response = self.client.get("/api/v1/projects/?freshness=invalid")

        self.assertEqual(response.status_code, 400)
        self.assertIn("must be a valid number", response.json()["error"])

    def test_filter_freshness_decimal_value(self):
        """Test filtering with decimal freshness value"""
        response = self.client.get("/api/v1/projects/?freshness=50.5")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Should return projects with freshness >= 50.5
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["name"], "High Freshness")

    def test_filter_freshness_combined_with_other_filters(self):
        """Test freshness filter combined with other filters"""
        # Add repos for star filtering
        Repo.objects.create(
            project=self.high_freshness_project,
            name="popular-repo",
            repo_url="https://github.com/test/popular",
            stars=1000,
            forks=100,
        )
        Repo.objects.create(
            project=self.low_freshness_project,
            name="unpopular-repo",
            repo_url="https://github.com/test/unpopular",
            stars=10,
            forks=5,
        )

        # Filter by both freshness and stars
        response = self.client.get("/api/v1/projects/?freshness=50&stars=500")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Should return only high freshness project with enough stars
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["results"][0]["name"], "High Freshness")

    def test_filter_without_freshness_parameter(self):
        """Test that filtering works when freshness parameter is not provided"""
        response = self.client.get("/api/v1/projects/")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Should return all projects
        self.assertEqual(len(data["results"]), 4)

    def test_freshness_field_in_api_response(self):
        """Test that freshness field is included in API response"""
        response = self.client.get("/api/v1/projects/")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Check that freshness field exists in response
        for project in data["results"]:
            self.assertIn("freshness", project)
            self.assertIsNotNone(project["freshness"])
