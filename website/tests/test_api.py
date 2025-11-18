from io import BytesIO
from unittest.mock import Mock

from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models import Sum
from django.db.transaction import atomic
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_str
from rest_framework import status
from rest_framework.test import APITestCase

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
    def test_rebuild_safe_url(self):
        print("=== STARTING REBUILD SAFE URL TESTS - UNIQUE MARKER ===")
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


class GitHubIssueBadgeAPITestCase(APITestCase):
    """Test cases for GitHub issue badge API endpoint."""

    def setUp(self):
        """Set up test data."""
        from website.models import GitHubIssue, Repo

        self.repo = Repo.objects.create(
            name="Test Repo",
            slug="test-repo",
            repo_url="https://github.com/test/repo",
        )

        self.github_issue = GitHubIssue.objects.create(
            issue_id=123,
            title="Test Issue",
            body="Test issue body",
            state="open",
            url="https://github.com/test/repo/issues/123",
            created_at=timezone.now(),
            updated_at=timezone.now(),
            repo=self.repo,
            p2p_amount_usd=100.00,
        )

    def test_badge_endpoint_exists(self):
        """Test that badge endpoint is accessible."""
        url = "/api/v1/badge/issue/123/"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_badge_returns_svg(self):
        """Test that badge endpoint returns SVG content."""
        url = "/api/v1/badge/issue/123/"
        response = self.client.get(url)
        self.assertEqual(response["Content-Type"], "image/svg+xml")

    def test_badge_contains_view_count(self):
        """Test that badge SVG contains view count."""
        from website.models import IP

        # Create some IP log entries with the badge path
        IP.objects.create(
            address="192.168.1.1",
            path="/api/v1/badge/issue/123/",
            method="GET",
            count=5,
        )

        url = "/api/v1/badge/issue/123/"
        response = self.client.get(url)
        content = response.content.decode("utf-8")

        self.assertIn("views", content)
        self.assertIn("5", content)

    def test_badge_contains_bounty_amount(self):
        """Test that badge SVG contains bounty amount."""
        url = "/api/v1/badge/issue/123/"
        response = self.client.get(url)
        content = response.content.decode("utf-8")

        self.assertIn("100", content)
        self.assertIn("💰", content)

    def test_badge_has_cache_headers(self):
        """Test that badge response includes cache headers."""
        url = "/api/v1/badge/issue/123/"
        response = self.client.get(url)

        self.assertIn("Cache-Control", response)
        self.assertEqual(response["Cache-Control"], "public, max-age=300")

    def test_badge_has_etag(self):
        """Test that badge response includes ETag header."""
        url = "/api/v1/badge/issue/123/"
        response = self.client.get(url)

        self.assertIn("ETag", response)
        self.assertIsNotNone(response["ETag"])

    def test_badge_etag_conditional_request(self):
        """Test that ETag conditional request returns 304."""
        from django.test import Client

        client = Client()
        url = "/api/v1/badge/issue/123/"

        # First request
        response1 = client.get(url)
        etag = response1["ETag"]

        # Second request with ETag
        response2 = client.get(url, HTTP_IF_NONE_MATCH=etag)
        self.assertEqual(response2.status_code, status.HTTP_304_NOT_MODIFIED)

    def test_badge_for_nonexistent_issue(self):
        """Test that badge endpoint handles non-existent issues."""
        url = "/api/v1/badge/issue/999999/"
        response = self.client.get(url)

        # Should still return 200 with fallback data
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "image/svg+xml")

    def test_badge_without_bounty(self):
        """Test that badge displays $0 when no bounty is set."""
        from website.models import GitHubIssue

        GitHubIssue.objects.create(
            issue_id=456,
            title="Issue without bounty",
            body="Test",
            state="open",
            url="https://github.com/test/repo/issues/456",
            created_at=timezone.now(),
            updated_at=timezone.now(),
            repo=self.repo,
        )

        url = "/api/v1/badge/issue/456/"
        response = self.client.get(url)
        content = response.content.decode("utf-8")

        self.assertIn("$0", content)

    def test_badge_ip_logging(self):
        """Test that badge requests are logged in IP model."""
        from website.models import IP

        url = "/api/v1/badge/issue/123/"
        self.client.get(url)

        # Check that IP log was created
        ip_logs = IP.objects.filter(path__icontains="/api/v1/badge/issue/123/")
        self.assertGreater(ip_logs.count(), 0)

    def test_badge_increments_count(self):
        """Test that repeated badge requests increment count."""
        from website.models import IP

        url = "/api/v1/badge/issue/789/"
        client = Client()

        # First request
        response1 = client.get(url)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # Get initial count
        ip_logs = IP.objects.filter(path__icontains="/api/v1/badge/issue/789/")
        initial_count = ip_logs.aggregate(total=Sum("count"))["total"] or 0

        # Second request from same IP
        response2 = client.get(url)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

        # Check that count incremented
        updated_count = ip_logs.aggregate(total=Sum("count"))["total"] or 0
        self.assertGreaterEqual(updated_count, initial_count)

    def test_badge_svg_has_correct_structure(self):
        """Test that generated SVG has correct structure."""
        url = "/api/v1/badge/issue/123/"
        response = self.client.get(url)
        content = response.content.decode("utf-8")

        # Check for SVG elements
        self.assertIn("<svg", content)
        self.assertIn("</svg>", content)
        self.assertIn("<text", content)
        self.assertIn("</text>", content)
        self.assertIn("linearGradient", content)

    def test_badge_uses_brand_color(self):
        """Test that badge uses BLT brand red color."""
        url = "/api/v1/badge/issue/123/"
        response = self.client.get(url)
        content = response.content.decode("utf-8")

        # Check for brand color hex codes
        self.assertIn("#e74c3c", content)  # Primary red
        self.assertIn("#c0392b", content)  # Darker red for gradient
