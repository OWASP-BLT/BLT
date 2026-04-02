from allauth.account.models import EmailAddress
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from website.models import Domain, Issue

User = get_user_model()


class IssueActionsApiTestBase(APITestCase):
    """Shared setup for issue action API tests (like, flag, delete)."""

    def setUp(self):
        self.owner = User.objects.create_user(username="owner", email="owner@test.com", password="TestPass123!")
        EmailAddress.objects.create(user=self.owner, email="owner@test.com", verified=True, primary=True)
        self.owner_token = Token.objects.get(user=self.owner)

        self.other_user = User.objects.create_user(username="other", email="other@test.com", password="TestPass123!")
        EmailAddress.objects.create(user=self.other_user, email="other@test.com", verified=True, primary=True)
        self.other_token = Token.objects.get(user=self.other_user)

        self.admin = User.objects.create_superuser(username="admin", email="admin@test.com", password="TestPass123!")
        self.admin_token = Token.objects.get(user=self.admin)

        self.domain = Domain.objects.create(url="https://example.com", name="example.com")
        self.issue = Issue.objects.create(
            user=self.owner,
            domain=self.domain,
            url="https://example.com/page",
            description="Test issue for API tests",
        )

    def auth_header(self, token):
        return {"HTTP_AUTHORIZATION": f"Token {token.key}"}


class LikeIssueApiViewTests(IssueActionsApiTestBase):
    def get_url(self, issue_id):
        return f"/api/v1/issue/like/{issue_id}/"

    def test_get_like_count_unauthenticated_rejected(self):
        response = self.client.get(self.get_url(self.issue.id))
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_get_like_count_authenticated(self):
        response = self.client.get(self.get_url(self.issue.id), **self.auth_header(self.other_token))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["likes"], 0)

    def test_like_requires_authentication(self):
        response = self.client.post(self.get_url(self.issue.id))
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_like_and_unlike_issue(self):
        response = self.client.post(self.get_url(self.issue.id), **self.auth_header(self.other_token))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["issue"], "liked")

        response = self.client.get(self.get_url(self.issue.id), **self.auth_header(self.other_token))
        self.assertEqual(response.data["likes"], 1)

        response = self.client.post(self.get_url(self.issue.id), **self.auth_header(self.other_token))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["issue"], "unliked")

        response = self.client.get(self.get_url(self.issue.id), **self.auth_header(self.other_token))
        self.assertEqual(response.data["likes"], 0)


class FlagIssueApiViewTests(IssueActionsApiTestBase):
    def get_url(self, issue_id):
        return f"/api/v1/issue/flag/{issue_id}/"

    def test_get_flag_count_unauthenticated_rejected(self):
        response = self.client.get(self.get_url(self.issue.id))
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_get_flag_count_authenticated(self):
        response = self.client.get(self.get_url(self.issue.id), **self.auth_header(self.other_token))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["flags"], 0)

    def test_flag_requires_authentication(self):
        response = self.client.post(self.get_url(self.issue.id))
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_flag_and_unflag_issue(self):
        response = self.client.post(self.get_url(self.issue.id), **self.auth_header(self.other_token))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["issue"], "flagged")

        response = self.client.get(self.get_url(self.issue.id), **self.auth_header(self.other_token))
        self.assertEqual(response.data["flags"], 1)

        response = self.client.post(self.get_url(self.issue.id), **self.auth_header(self.other_token))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["issue"], "unflagged")

        response = self.client.get(self.get_url(self.issue.id), **self.auth_header(self.other_token))
        self.assertEqual(response.data["flags"], 0)


class DeleteIssueApiViewTests(IssueActionsApiTestBase):
    def get_url(self, issue_id):
        return f"/api/v1/delete_issue/{issue_id}/"

    def test_delete_requires_authentication(self):
        response = self.client.delete(self.get_url(self.issue.id))
        self.assertIn(response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN])

    def test_non_owner_cannot_delete(self):
        response = self.client.delete(self.get_url(self.issue.id), **self.auth_header(self.other_token))
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Issue.objects.filter(id=self.issue.id).exists())

    def test_owner_can_delete(self):
        response = self.client.delete(self.get_url(self.issue.id), **self.auth_header(self.owner_token))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Issue.objects.filter(id=self.issue.id).exists())

    def test_admin_can_delete(self):
        response = self.client.delete(self.get_url(self.issue.id), **self.auth_header(self.admin_token))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Issue.objects.filter(id=self.issue.id).exists())

    def test_delete_nonexistent_issue(self):
        response = self.client.delete(self.get_url(99999), **self.auth_header(self.admin_token))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
