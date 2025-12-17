from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


class LoginTestCase(TestCase):
    """Test cases for login functionality with username/email support"""

    def setUp(self):
        """Set up test client and users"""
        self.client = Client()
        self.login_url = reverse("account_login")

        # Create a verified user for successful login tests
        self.test_user = User.objects.create_user(username="testuser", email="test@example.com", password="password123")
        EmailAddress.objects.create(user=self.test_user, email="test@example.com", verified=True, primary=True)

    def _assert_login_error_rendered(self, response):
        """Helper to verify login error is properly displayed"""
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)
        form = response.context["form"]
        self.assertTrue(form.non_field_errors(), "Expected non-field errors on the form, but found none.")
        self.assertContains(response, 'role="alert"')
        self.assertRegex(
            response.content.decode(),
            r"(email address|e-mail address|username|login).*(and/or|or).*(password|credentials).*(not correct|incorrect|invalid)",
            "Expected login error message not found in response",
        )

    # ----------------------- INVALID LOGIN TESTS -----------------------
    def test_login_with_invalid_username_shows_error(self):
        response = self.client.post(self.login_url, {"login": "nonexistent_user", "password": "wrongpassword"})
        self._assert_login_error_rendered(response)

    def test_login_with_invalid_email_shows_error(self):
        response = self.client.post(self.login_url, {"login": "nonexistent@example.com", "password": "wrongpassword"})
        self._assert_login_error_rendered(response)

    def test_login_with_correct_username_wrong_password(self):
        response = self.client.post(self.login_url, {"login": "testuser", "password": "wrongpassword"})
        self._assert_login_error_rendered(response)

    def test_login_with_correct_email_wrong_password(self):
        response = self.client.post(self.login_url, {"login": "test@example.com", "password": "wrongpassword"})
        self._assert_login_error_rendered(response)

    # ----------------------- SUCCESSFUL LOGIN TESTS -----------------------
    def test_login_with_email_success(self):
        response = self.client.post(
            self.login_url, {"login": "test@example.com", "password": "password123"}, follow=False
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_with_username_success(self):
        response = self.client.post(self.login_url, {"login": "testuser", "password": "password123"}, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_email_case_insensitive(self):
        response = self.client.post(
            self.login_url, {"login": "TEST@EXAMPLE.COM", "password": "password123"}, follow=False
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_with_whitespace_in_username(self):
        response = self.client.post(self.login_url, {"login": "  testuser  ", "password": "password123"}, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_with_next_parameter(self):
        response = self.client.post(
            f"{self.login_url}?next=/profile/", {"login": "testuser", "password": "password123"}, follow=False
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/profile/", response.url)

    # ----------------------- EMPTY FIELD TESTS -----------------------
    def test_login_with_empty_username(self):
        response = self.client.post(self.login_url, {"login": "", "password": "password123"}, follow=True)
        form = response.context.get("form")
        self.assertIsNotNone(form)
        self.assertIn("login", form.errors)
        self.assertEqual(form.errors["login"], ["This field is required."])

    def test_login_with_empty_password(self):
        response = self.client.post(self.login_url, {"login": "testuser", "password": ""}, follow=True)
        form = response.context.get("form")
        self.assertIsNotNone(form)
        self.assertIn("password", form.errors)
        self.assertEqual(form.errors["password"], ["This field is required."])

    def test_login_with_both_fields_empty(self):
        response = self.client.post(self.login_url, {"login": "", "password": ""}, follow=True)
        form = response.context.get("form")
        self.assertIsNotNone(form)
        self.assertIn("login", form.errors)
        self.assertIn("password", form.errors)
        self.assertEqual(form.errors["login"], ["This field is required."])
        self.assertEqual(form.errors["password"], ["This field is required."])

    # ----------------------- UNVERIFIED EMAIL TEST -----------------------
    def test_login_with_unverified_email(self):
        unverified_user = User.objects.create_user(
            username="unverified", email="unverified@example.com", password="password123"
        )
        EmailAddress.objects.create(user=unverified_user, email="unverified@example.com", verified=False, primary=True)

        response = self.client.post(
            self.login_url, {"login": "unverified@example.com", "password": "password123"}, follow=False
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/confirm-email/", response.url)
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    # ----------------------- PAGE RENDER TESTS -----------------------
    def test_login_page_renders_correctly(self):
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Username or Email")

    def test_login_displays_error_alert_styling(self):
        response = self.client.post(self.login_url, {"login": "invalid", "password": "wrong"})
        self.assertContains(response, "bg-red-100")
        self.assertContains(response, "border-red-500")
        self.assertContains(response, "text-red-700")
