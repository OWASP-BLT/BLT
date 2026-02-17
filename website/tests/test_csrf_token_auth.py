"""
Tests to verify token-based authentication endpoints continue working after CSRF protection changes.
Addresses PR #5812: Remove csrf_exempt from mutating API endpoints

Key behaviors verified:
1. Token-authenticated requests work without CSRF tokens (mobile app compatibility)
2. GET endpoints don't require CSRF (harmless but correct)
3. Session-authenticated requests require CSRF (security improvement)
"""

from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from website.models import Issue, Domain

User = get_user_model()


class TokenBasedAuthTest(TestCase):
    """Test that token-based API endpoints work without CSRF requirements."""

    def setUp(self):
        """Set up test user and token."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.token, _ = Token.objects.get_or_create(user=self.user)
        
        self.domain = Domain.objects.create(name="example.com", url="example.com")
        self.issue = Issue.objects.create(
            url="https://example.com/test",
            description="Test vulnerability",
            domain=self.domain,
            user=self.user,
            label=1,
        )

    def test_api_client_with_token_auth_no_csrf_error(self):
        """
        Token-authenticated requests should work without CSRF tokens.
        This ensures mobile app and external API clients function correctly.
        The key is: we should NOT get a 403 CSRF error.
        """
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        # POST to token-protected endpoint with minimal data
        # The endpoint may return other errors (400 validation, etc), 
        # but NOT 403 CSRF Forbidden
        response = client.post('/api/v1/issue/update/', {
            "id": self.issue.id,
            "description": "Updated",
        }, format='json')
        
        # Should NOT be 403 CSRF error (token auth bypasses CSRF)
        self.assertNotEqual(response.status_code, 403,
                           msg="Token auth should bypass CSRF requirement")

    def test_token_auth_on_update_endpoint(self):
        """Token auth should work on UpdateIssue endpoint without CSRF error."""
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f'Token {self.token.key}')
        
        response = client.post(f'/api/v1/issue/update/', {
            "id": self.issue.id,
            "description": "Updated",
        }, format='json')
        
        # Should NOT be 403 CSRF error
        self.assertNotEqual(response.status_code, 403,
                           msg="Token auth should bypass CSRF on update")

    def test_get_request_never_requires_csrf(self):
        """GET requests should never fail with CSRF errors."""
        client = APIClient()
        
        # No auth, no CSRF token - GET request
        response = client.get('/api/v1/search/?query=test')
        
        # Should not be 403 CSRF error (GET is safe, doesn't need CSRF)
        self.assertNotEqual(response.status_code, 403,
                           msg="GET requests should not fail with CSRF error")


class SessionAuthCSRFTest(TestCase):
    """Test that session-authenticated endpoints now enforce CSRF properly."""

    def setUp(self):
        """Set up test user and login."""
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123"
        )
        self.domain = Domain.objects.create(name="example.com", url="example.com")
        self.issue = Issue.objects.create(
            url="https://example.com/test",
            description="Test vulnerability",
            domain=self.domain,
            user=self.user,
            label=1,
        )

    def test_session_auth_without_csrf_fails(self):
        """
        Session-authenticated requests without CSRF tokens should fail with 403.
        This is the security improvement: CSRF protection is now enforced.
        """
        client = Client(enforce_csrf_checks=True)
        
        # Login with session
        client.login(username="testuser", password="testpass123")
        
        # Attempt POST without CSRF token
        response = client.post(f'/api/v1/delete_issue/{self.issue.id}/', {})
        
        # Should fail with 403 CSRF error (this is correct behavior)
        self.assertEqual(response.status_code, 403,
                        msg="Session auth without CSRF token should fail with 403")
    
    def test_session_auth_with_csrf_succeeds(self):
        client = Client(enforce_csrf_checks=True)
        client.login(username="testuser", password="testpass123")

        # get CSRF token
        response = client.get("/", follow=True)
        csrf_token = response.cookies.get("csrftoken").value

        response = client.post(
            f'/api/v1/delete_issue/{self.issue.id}/',
            {},
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertNotEqual(response.status_code, 403)
        self.assertNotEqual(response.status_code, 401)
