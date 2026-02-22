"""
Tests to verify token-based authentication endpoints continue working after CSRF protection changes.
Addresses PR #5812: Remove csrf_exempt from mutating API endpoints

Key behaviors verified:
1. Token-authenticated requests work without CSRF tokens (mobile app compatibility)
2. GET endpoints don't require CSRF (harmless but correct)
3. Session-authenticated requests require CSRF (security improvement)
"""

from django.contrib.auth import get_user_model
from django.middleware.csrf import get_token
from django.test import Client, TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from website.models import Domain, Issue

User = get_user_model()


class GetRequestNoCsrfTest(TestCase):
    """Test that GET requests never require CSRF."""

    def test_get_request_never_requires_csrf(self):
        """GET requests should never fail with CSRF errors."""
        client = APIClient()

        # No auth, no CSRF token - GET request
        response = client.get("/api/v1/search/?query=test")

        # Should not be 403 CSRF error (GET is safe, doesn't need CSRF)
        self.assertNotEqual(response.status_code, 403, msg="GET requests should not fail with CSRF error")


class SessionAuthWebViewTest(TestCase):
    """Test that session-authenticated web view endpoints enforce CSRF properly."""

    def setUp(self):
        """Set up test user and issue."""
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.domain = Domain.objects.create(name="example.com", url="example.com")
        self.issue = Issue.objects.create(
            url="https://example.com/test",
            description="Test vulnerability",
            domain=self.domain,
            user=self.user,
            label=1,
        )

    def test_session_auth_without_csrf_fails_on_web_view(self):
        """
        Session-authenticated DELETE requests without CSRF tokens should fail with 403.
        This tests the web view endpoint: DELETE /delete_issue/<id>/
        This is the security improvement: CSRF protection is now enforced.
        """
        client = Client(enforce_csrf_checks=True)

        # Login with session
        client.login(username="testuser", password="testpass123")

        # Attempt DELETE without CSRF token on web view endpoint
        response = client.post(f"/delete_issue/{self.issue.id}/", {})

        # Should fail with 403 CSRF error (this is correct behavior)
        self.assertEqual(response.status_code, 403, msg="Session auth without CSRF token should fail with 403")

    def test_session_auth_with_csrf_succeeds_on_web_view(self):
        """
        Session-authenticated DELETE requests with CSRF tokens should succeed.
        This tests the web view endpoint: DELETE /delete_issue/<id>/
        """
        client = Client(enforce_csrf_checks=True)

        # Login with session
        client.login(username="testuser", password="testpass123")

        # Generate and set CSRF token for this session
        response = client.get("/")
        csrf_token = get_token(response.wsgi_request)
        client.cookies["csrftoken"] = csrf_token

        response = client.post(
            f"/delete_issue/{self.issue.id}/",
            {},
            HTTP_X_CSRFTOKEN=csrf_token,
        )

        self.assertEqual(response.status_code, 200, msg="Session auth with CSRF token should succeed")
        self.assertFalse(
            Issue.objects.filter(id=self.issue.id).exists(),
            msg="Issue should be deleted after CSRF-protected request",
        )


class TokenAuthApiViewTest(TestCase):
    """Test that token-authenticated API endpoints work without CSRF."""

    def setUp(self):
        """Set up test user, token, and issue."""
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.token, _ = Token.objects.get_or_create(user=self.user)
        self.domain = Domain.objects.create(name="example.com", url="example.com")
        self.issue = Issue.objects.create(
            url="https://example.com/test",
            description="Test vulnerability",
            domain=self.domain,
            user=self.user,
            label=1,
        )

    def test_token_delete_succeeds_on_api_view(self):
        """
        Token-authenticated DELETE requests should succeed without CSRF tokens.
        This tests the API endpoint: DELETE /api/v1/delete_issue/<id>/
        Token auth must work without CSRF for mobile app compatibility.
        """
        client = APIClient()

        # DELETE with token auth, no CSRF token
        response = client.delete(
            f"/api/v1/delete_issue/{self.issue.id}/",
            HTTP_AUTHORIZATION=f"Token {self.token.key}",
        )

        # Should succeed with 200 OK
        self.assertEqual(response.status_code, 200, msg="Token-authenticated DELETE should succeed")

        # Verify the issue is actually deleted
        self.assertFalse(
            Issue.objects.filter(id=self.issue.id).exists(),
            msg="Issue should be deleted after successful DELETE request",
        )
