from django.contrib.auth import get_user_model
from django.core import mail
from django.db.transaction import atomic
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_str
from rest_framework import status
from rest_framework.test import APITestCase

from website.utils import rebuild_safe_url


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
        self.assertIn("key", result.data)
        self.assertEqual(get_user_model().objects.all().count(), user_count + 1)

        new_user = get_user_model().objects.latest("id")
        self.assertEqual(new_user.username, self.REGISTRATION_DATA["username"])

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
