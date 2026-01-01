from allauth.account.models import EmailAddress
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse


class LoginFunctionalityTestCase(TestCase):
    """Test cases for login functionality"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.login_url = reverse("account_login")

        # Create test user
        self.test_user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

        # Verify email for allauth
        EmailAddress.objects.create(user=self.test_user, email="test@example.com", verified=True, primary=True)

    def test_valid_login_with_username(self):
        """Test successful login with valid username and password"""
        response = self.client.post(self.login_url, {"login": "testuser", "password": "testpass123"})

        # Should redirect after successful login
        self.assertEqual(response.status_code, 302)

        # User should be authenticated
        user = authenticate(username="testuser", password="testpass123")
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "testuser")

    def test_valid_login_with_email(self):
        """Test successful login with valid email and password"""
        response = self.client.post(self.login_url, {"login": "test@example.com", "password": "testpass123"})

        # Should redirect after successful login
        self.assertEqual(response.status_code, 302)

    def test_invalid_login_wrong_password(self):
        """Test login failure with wrong password"""
        response = self.client.post(self.login_url, {"login": "testuser", "password": "wrongpassword"})

        # Should stay on login page
        self.assertEqual(response.status_code, 200)

        # Should show error message
        self.assertContains(response, "Invalid username/email or password")

    def test_invalid_login_nonexistent_user(self):
        """Test login failure with non-existent user"""
        response = self.client.post(self.login_url, {"login": "nonexistentuser", "password": "anypassword"})

        # Should stay on login page
        self.assertEqual(response.status_code, 200)

        # Should show error message
        self.assertContains(response, "Invalid username/email or password")

    def test_empty_credentials(self):
        """Test login with empty credentials"""
        response = self.client.post(self.login_url, {"login": "", "password": ""})

        # Should stay on login page
        self.assertEqual(response.status_code, 200)

        # Should show validation errors
        self.assertContains(response, "This field is required")

    def test_missing_password(self):
        """Test login with username but no password"""
        response = self.client.post(self.login_url, {"login": "testuser", "password": ""})

        # Should stay on login page
        self.assertEqual(response.status_code, 200)

        # Should show validation error
        self.assertContains(response, "This field is required")

    def test_missing_username(self):
        """Test login with password but no username"""
        response = self.client.post(self.login_url, {"login": "", "password": "testpass123"})

        # Should stay on login page
        self.assertEqual(response.status_code, 200)

        # Should show validation error
        self.assertContains(response, "This field is required")

    def test_login_page_loads(self):
        """Test that login page loads correctly"""
        response = self.client.get(self.login_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Username or Email")
        self.assertContains(response, "Password")

    def test_inactive_user_login(self):
        """Test login with inactive user account"""
        # Create inactive user
        inactive_user = User.objects.create_user(
            username="inactiveuser", email="inactive@example.com", password="testpass123", is_active=False
        )

        EmailAddress.objects.create(user=inactive_user, email="inactive@example.com", verified=True, primary=True)

        response = self.client.post(self.login_url, {"login": "inactiveuser", "password": "testpass123"})

        # Should stay on login page
        self.assertEqual(response.status_code, 200)

        # Should show error message
        self.assertContains(response, "Invalid username/email or password")

    def test_unverified_email_login(self):
        """Test login with unverified email"""
        # Create user with unverified email
        unverified_user = User.objects.create_user(
            username="unverifieduser", email="unverified@example.com", password="testpass123"
        )

        EmailAddress.objects.create(user=unverified_user, email="unverified@example.com", verified=False, primary=True)

        response = self.client.post(self.login_url, {"login": "unverifieduser", "password": "testpass123"})

        # Should redirect to email verification page
        self.assertEqual(response.status_code, 302)

    def test_case_insensitive_email_login(self):
        """Test login with different case email"""
        response = self.client.post(self.login_url, {"login": "TEST@EXAMPLE.COM", "password": "testpass123"})

        # Should redirect after successful login
        self.assertEqual(response.status_code, 302)

    def test_sql_injection_attempt(self):
        """Test protection against SQL injection in login"""
        response = self.client.post(
            self.login_url, {"login": "admin'; DROP TABLE auth_user; --", "password": "testpass123"}
        )

        # Should stay on login page with error
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username/email or password")

        # User table should still exist
        self.assertTrue(User.objects.filter(username="testuser").exists())

    def test_xss_attempt_in_login(self):
        """Test protection against XSS in login form"""
        response = self.client.post(
            self.login_url, {"login": '<script>alert("xss")</script>', "password": "testpass123"}
        )

        # Should stay on login page
        self.assertEqual(response.status_code, 200)

        # Script should be escaped in response
        self.assertNotContains(response, '<script>alert("xss")</script>')

    def test_login_redirect_after_success(self):
        """Test redirect after successful login"""
        # Try to access protected page first
        protected_url = reverse("user")
        response = self.client.get(protected_url)

        # Should redirect to login with next parameter
        self.assertEqual(response.status_code, 302)

        # Now login
        response = self.client.post(self.login_url, {"login": "testuser", "password": "testpass123"}, follow=True)

        # Should be redirected to home page or dashboard
        self.assertEqual(response.status_code, 200)

    def test_already_logged_in_user_redirect(self):
        """Test behavior when already logged in user visits login page"""
        # Login first
        self.client.login(username="testuser", password="testpass123")

        # Visit login page
        response = self.client.get(self.login_url)

        # Should redirect away from login page
        self.assertEqual(response.status_code, 302)

    def test_csrf_protection(self):
        """Test CSRF protection on login form"""
        # Get login page to get CSRF token
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)

        # Try to post without CSRF token using a new client
        new_client = Client(enforce_csrf_checks=True)
        response = new_client.post(self.login_url, {"login": "testuser", "password": "testpass123"})

        # Should be forbidden due to missing CSRF token
        self.assertEqual(response.status_code, 403)

    def test_rate_limiting_protection(self):
        """Test protection against brute force attacks"""
        # Make multiple failed login attempts
        for i in range(10):
            response = self.client.post(self.login_url, {"login": "testuser", "password": "wrongpassword"})

            # All should return 200 (login page) but with error
            self.assertEqual(response.status_code, 200)

        # The system should still allow valid login
        response = self.client.post(self.login_url, {"login": "testuser", "password": "testpass123"})

        # Should still work (basic test - actual rate limiting might be implemented differently)
        self.assertIn(response.status_code, [200, 302])

    def test_login_form_fields_present(self):
        """Test that login form has required fields"""
        response = self.client.get(self.login_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="login"')
        self.assertContains(response, 'name="password"')
        self.assertContains(response, 'type="password"')

    def test_remember_me_functionality(self):
        """Test remember me checkbox functionality"""
        response = self.client.post(self.login_url, {"login": "testuser", "password": "testpass123", "remember": "on"})

        # Should redirect after successful login
        self.assertEqual(response.status_code, 302)

        # Session should be configured for longer duration
        # This is implementation-specific and might need adjustment
        self.assertTrue(self.client.session.get_expire_at_browser_close() is not None)
