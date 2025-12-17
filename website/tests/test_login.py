from allauth.account.models import EmailAddress
from django.contrib.auth.models import User
from django.test import Client, TestCase


class LoginTestCase(TestCase):
    """Test cases for login functionality with username/email support"""

    def setUp(self):
        """Set up test client and users"""
        self.client = Client()
        # Create a verified user for successful login tests
        self.test_user = User.objects.create_user(username="testuser", email="test@example.com", password="password123")
        EmailAddress.objects.create(user=self.test_user, email="test@example.com", verified=True, primary=True)

    def test_login_with_invalid_username_shows_error(self):
        """Test that invalid username displays non-field error"""
        response = self.client.post("/accounts/login/", {"login": "nonexistent_user", "password": "wrongpassword"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "non_field_errors")

    def test_login_with_invalid_email_shows_error(self):
        """Test that invalid email displays non-field error"""
        response = self.client.post(
            "/accounts/login/", {"login": "nonexistent@example.com", "password": "wrongpassword"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "non_field_errors")

    def test_login_with_email_success(self):
        """Test successful login using email instead of username"""
        response = self.client.post(
            "/accounts/login/", {"login": "test@example.com", "password": "password123"}, follow=False
        )
        self.assertEqual(response.status_code, 302)  # Redirect on success
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_with_username_success(self):
        """Test successful login using username (existing functionality)"""
        response = self.client.post("/accounts/login/", {"login": "testuser", "password": "password123"}, follow=False)
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.wsgi_request.user.is_authenticated)

    def test_login_with_correct_username_wrong_password(self):
        """Test error when username exists but password is wrong"""
        response = self.client.post("/accounts/login/", {"login": "testuser", "password": "wrongpassword"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "non_field_errors")
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_with_correct_email_wrong_password(self):
        """Test error when email exists but password is wrong"""
        response = self.client.post("/accounts/login/", {"login": "test@example.com", "password": "wrongpassword"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "non_field_errors")
        self.assertFalse(response.wsgi_request.user.is_authenticated)

    def test_login_with_empty_username(self):
        """Test that empty login field shows appropriate error"""
        response = self.client.post("/accounts/login/", {"login": "", "password": "password123"})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "login", "This field is required.")

    def test_login_with_empty_password(self):
        """Test that empty password field shows appropriate error"""
        response = self.client.post("/accounts/login/", {"login": "testuser", "password": ""})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "password", "This field is required.")

    def test_login_with_both_fields_empty(self):
        """Test that empty form shows errors for both fields"""
        response = self.client.post("/accounts/login/", {"login": "", "password": ""})
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response, "form", "login", "This field is required.")
        self.assertFormError(response, "form", "password", "This field is required.")

    def test_login_with_unverified_email(self):
        """Test that unverified users cannot login (ACCOUNT_EMAIL_VERIFICATION='mandatory')"""
        # Create unverified user
        unverified_user = User.objects.create_user(
            username="unverified", email="unverified@example.com", password="password123"
        )
        EmailAddress.objects.create(user=unverified_user, email="unverified@example.com", verified=False, primary=True)

        response = self.client.post(
            "/accounts/login/", {"login": "unverified@example.com", "password": "password123"}, follow=False
        )

        # With mandatory verification, allauth logs the user in but redirects them to the email verification page.
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/confirm-email/", response.url)  # User is redirected to verify email
        self.assertFalse(response.wsgi_request.user.is_authenticated)  # User is NOT logged in

    def test_login_email_case_insensitive(self):
        """Test that email login is case-insensitive"""
        response = self.client.post(
            "/accounts/login/", {"login": "TEST@EXAMPLE.COM", "password": "password123"}, follow=False
        )
        # Email matching should be case-insensitive
        self.assertEqual(response.status_code, 302)

    def test_login_with_whitespace_in_username(self):
        """Test that whitespace is handled properly"""
        response = self.client.post("/accounts/login/", {"login": "  testuser  ", "password": "password123"})
        # Allauth should strip whitespace
        self.assertEqual(response.status_code, 302)

    def test_login_with_next_parameter(self):
        """Test that next parameter redirects to correct page after login"""
        response = self.client.post(
            "/accounts/login/?next=/profile/", {"login": "testuser", "password": "password123"}, follow=False
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("/profile/", response.url)

    def test_login_page_renders_correctly(self):
        """Test that login page renders with proper label"""
        response = self.client.get("/accounts/login/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Username or Email")

    def test_login_displays_error_alert_styling(self):
        """Test that error message has proper styling classes"""
        response = self.client.post("/accounts/login/", {"login": "invalid", "password": "wrong"})
        self.assertContains(response, "bg-red-100")
        self.assertContains(response, "border-red-500")
        self.assertContains(response, "text-red-700")
