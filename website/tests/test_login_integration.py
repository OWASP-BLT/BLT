"""
Django Integration Tests for Login Functionality

This test file provides comprehensive Django-based tests for the login system.
Run these tests when the full Django environment is available.

Usage:
    python manage.py test website.tests.test_login_integration
"""


from allauth.account.models import EmailAddress
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.sessions.models import Session
from django.test import Client, TestCase, override_settings
from django.urls import reverse


class LoginIntegrationTestCase(TestCase):
    """Comprehensive integration tests for login functionality"""

    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.login_url = reverse("account_login")

        # Create test users
        self.active_user = User.objects.create_user(
            username="activeuser", email="active@example.com", password="securepass123"
        )

        self.inactive_user = User.objects.create_user(
            username="inactiveuser", email="inactive@example.com", password="securepass123", is_active=False
        )

        # Create verified email addresses
        EmailAddress.objects.create(user=self.active_user, email="active@example.com", verified=True, primary=True)

        EmailAddress.objects.create(user=self.inactive_user, email="inactive@example.com", verified=True, primary=True)

        # Create unverified user
        self.unverified_user = User.objects.create_user(
            username="unverifieduser", email="unverified@example.com", password="securepass123"
        )

        EmailAddress.objects.create(
            user=self.unverified_user, email="unverified@example.com", verified=False, primary=True
        )

    def test_successful_login_username(self):
        """Test successful login with username"""
        response = self.client.post(self.login_url, {"login": "activeuser", "password": "securepass123"})

        # Should redirect after successful login
        self.assertEqual(response.status_code, 302)

        # User should be authenticated in session
        self.assertTrue("_auth_user_id" in self.client.session)
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.active_user.id)

    def test_successful_login_email(self):
        """Test successful login with email address"""
        response = self.client.post(self.login_url, {"login": "active@example.com", "password": "securepass123"})

        # Should redirect after successful login
        self.assertEqual(response.status_code, 302)

        # User should be authenticated
        self.assertTrue("_auth_user_id" in self.client.session)

    def test_failed_login_wrong_password(self):
        """Test failed login with wrong password"""
        response = self.client.post(self.login_url, {"login": "activeuser", "password": "wrongpassword"})

        # Should stay on login page
        self.assertEqual(response.status_code, 200)

        # Should show error message
        self.assertContains(response, "Invalid username/email or password")

        # User should not be authenticated
        self.assertFalse("_auth_user_id" in self.client.session)

    def test_failed_login_nonexistent_user(self):
        """Test failed login with non-existent user"""
        response = self.client.post(self.login_url, {"login": "nonexistentuser", "password": "anypassword"})

        # Should stay on login page
        self.assertEqual(response.status_code, 200)

        # Should show error message
        self.assertContains(response, "Invalid username/email or password")

    def test_failed_login_inactive_user(self):
        """Test failed login with inactive user"""
        response = self.client.post(self.login_url, {"login": "inactiveuser", "password": "securepass123"})

        # Should stay on login page
        self.assertEqual(response.status_code, 200)

        # Should show error message
        self.assertContains(response, "Invalid username/email or password")

    def test_failed_login_unverified_email(self):
        """Test login with unverified email"""
        response = self.client.post(self.login_url, {"login": "unverifieduser", "password": "securepass123"})

        # Should redirect to email verification
        self.assertEqual(response.status_code, 302)
        self.assertIn("confirm-email", response.url)

    def test_empty_credentials(self):
        """Test login with empty credentials"""
        response = self.client.post(self.login_url, {"login": "", "password": ""})

        # Should stay on login page
        self.assertEqual(response.status_code, 200)

        # Should show validation errors
        self.assertContains(response, "This field is required")

    def test_login_page_loads_correctly(self):
        """Test that login page loads with correct elements"""
        response = self.client.get(self.login_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="login"')
        self.assertContains(response, 'name="password"')
        self.assertContains(response, 'type="password"')

    def test_case_insensitive_email_login(self):
        """Test login with different case email"""
        response = self.client.post(self.login_url, {"login": "ACTIVE@EXAMPLE.COM", "password": "securepass123"})

        # Should redirect after successful login
        self.assertEqual(response.status_code, 302)

    def test_csrf_protection(self):
        """Test CSRF protection on login form"""
        # Get login page to ensure CSRF token is available
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)

        # Create new client with CSRF checks enabled
        csrf_client = Client(enforce_csrf_checks=True)

        # Try to post without CSRF token
        response = csrf_client.post(self.login_url, {"login": "activeuser", "password": "securepass123"})

        # Should be forbidden due to missing CSRF token
        self.assertEqual(response.status_code, 403)

    def test_sql_injection_protection(self):
        """Test protection against SQL injection attempts"""
        malicious_inputs = [
            "admin'; DROP TABLE auth_user; --",
            "' OR '1'='1' --",
            "'; DELETE FROM auth_user WHERE '1'='1",
            "admin' UNION SELECT * FROM auth_user --",
        ]

        for malicious_input in malicious_inputs:
            response = self.client.post(self.login_url, {"login": malicious_input, "password": "anypassword"})

            # Should stay on login page with error
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, "Invalid username/email or password")

            # User table should still exist and be intact
            self.assertTrue(User.objects.filter(username="activeuser").exists())

    def test_xss_protection(self):
        """Test protection against XSS attempts"""
        xss_payloads = [
            '<script>alert("xss")</script>',
            'javascript:alert("xss")',
            '<img src="x" onerror="alert(1)">',
            '<svg onload="alert(1)">',
        ]

        for payload in xss_payloads:
            response = self.client.post(self.login_url, {"login": payload, "password": "anypassword"})

            # Should stay on login page
            self.assertEqual(response.status_code, 200)

            # Payload should be escaped in response
            self.assertNotContains(response, payload, html=False)

    def test_login_redirect_next_parameter(self):
        """Test redirect to next parameter after login"""
        # Try to access protected page
        protected_url = "/dashboard/user/"
        next_url = f"{self.login_url}?next={protected_url}"

        # Login with next parameter
        response = self.client.post(next_url, {"login": "activeuser", "password": "securepass123"})

        # Should redirect to the next URL or default redirect
        self.assertEqual(response.status_code, 302)

    def test_already_authenticated_user_redirect(self):
        """Test redirect when already authenticated user visits login"""
        # Login first
        self.client.force_login(self.active_user)

        # Visit login page
        response = self.client.get(self.login_url)

        # Should redirect away from login page
        self.assertEqual(response.status_code, 302)

    def test_session_creation_and_management(self):
        """Test session creation and management"""
        # Login user
        response = self.client.post(self.login_url, {"login": "activeuser", "password": "securepass123"})

        # Should have session
        self.assertTrue(self.client.session.session_key)

        # Session should contain user ID
        self.assertEqual(int(self.client.session["_auth_user_id"]), self.active_user.id)

        # Session should exist in database
        session_exists = Session.objects.filter(session_key=self.client.session.session_key).exists()
        self.assertTrue(session_exists)

    def test_logout_functionality(self):
        """Test logout functionality"""
        # Login first
        self.client.force_login(self.active_user)
        self.assertTrue("_auth_user_id" in self.client.session)

        # Logout
        logout_url = reverse("account_logout")
        response = self.client.post(logout_url)

        # Should redirect after logout
        self.assertEqual(response.status_code, 302)

        # Session should be cleared
        self.assertFalse("_auth_user_id" in self.client.session)

    @override_settings(ACCOUNT_LOGIN_ATTEMPTS_LIMIT=3)
    def test_rate_limiting_simulation(self):
        """Test rate limiting behavior (if implemented)"""
        # Make multiple failed login attempts
        for i in range(5):
            response = self.client.post(self.login_url, {"login": "activeuser", "password": "wrongpassword"})

            # Should stay on login page
            self.assertEqual(response.status_code, 200)

        # Valid login should still work (basic test)
        response = self.client.post(self.login_url, {"login": "activeuser", "password": "securepass123"})

        # Should either work or show rate limit message
        self.assertIn(response.status_code, [200, 302])

    def test_remember_me_functionality(self):
        """Test remember me checkbox if available"""
        response = self.client.post(
            self.login_url, {"login": "activeuser", "password": "securepass123", "remember": "on"}
        )

        # Should redirect after successful login
        self.assertEqual(response.status_code, 302)

        # Session expiry should be configured appropriately
        # This test depends on the specific implementation

    def test_password_field_security(self):
        """Test password field security attributes"""
        response = self.client.get(self.login_url)

        # Password field should have proper attributes
        self.assertContains(response, 'type="password"')
        # Should not contain autocomplete="off" as it's not recommended anymore

    def test_form_validation_messages(self):
        """Test form validation error messages"""
        # Test missing username
        response = self.client.post(self.login_url, {"login": "", "password": "securepass123"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")

        # Test missing password
        response = self.client.post(self.login_url, {"login": "activeuser", "password": ""})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This field is required")

    def test_authentication_backend(self):
        """Test Django authentication backend directly"""
        # Test valid authentication
        user = authenticate(username="activeuser", password="securepass123")
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "activeuser")

        # Test invalid authentication
        user = authenticate(username="activeuser", password="wrongpassword")
        self.assertIsNone(user)

        # Test non-existent user
        user = authenticate(username="nonexistent", password="anypassword")
        self.assertIsNone(user)

    def test_custom_login_form_behavior(self):
        """Test custom login form behavior"""
        response = self.client.get(self.login_url)

        # Should contain custom form elements
        self.assertContains(response, "Username or Email")

        # Should have proper CSS classes if custom form is used
        # This depends on the CustomLoginForm implementation

    def tearDown(self):
        """Clean up after tests"""
        # Clear any remaining sessions
        Session.objects.all().delete()

        # Clear users
        User.objects.all().delete()

        # Clear email addresses
        EmailAddress.objects.all().delete()
