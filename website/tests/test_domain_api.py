from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from website.models import Domain

User = get_user_model()


class DomainViewSetPermissionTests(APITestCase):
    """Verify DomainViewSet enforces IsAuthenticatedOrReadOnly."""

    url = "/api/v1/domain/"

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser", email="test@test.com", password="TestPass123!"
        )
        EmailAddress.objects.create(user=self.user, email="test@test.com", verified=True, primary=True)
        self.token = Token.objects.get(user=self.user)
        Domain.objects.create(url="https://example.com", name="example.com")

    def test_unauthenticated_get_succeeds(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_post_rejected(self):
        response = self.client.post(self.url, data={"url": "https://new.com", "name": "new.com"})
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_authenticated_post_succeeds(self):
        response = self.client.post(
            self.url,
            data={"url": "https://new.com", "name": "new.com"},
            HTTP_AUTHORIZATION=f"Token {self.token.key}",
        )
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_201_CREATED])
