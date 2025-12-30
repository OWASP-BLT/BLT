from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from website.models import Domain, Organization, OrgEncryptionConfig, User


class ZeroTrustAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="apiuser", password="pass")
        self.token, _ = Token.objects.get_or_create(user=self.user)

        self.org = Organization.objects.create(name="API Org")
        self.domain = Domain.objects.create(organization=self.org, url="https://api.example.com")

        OrgEncryptionConfig.objects.create(
            organization=self.org,
            contact_email="security@example.com",
            preferred_method="age",
            age_recipient="age1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqq",
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token.key}")

    @patch("website.api.views.build_and_deliver_zero_trust_issue")
    def test_zero_trust_issue_creation(self, mock_pipeline):
        mock_pipeline.return_value = None
        url = "/api/zero-trust/issues/"

        file = SimpleUploadedFile(
            "exploit.txt",
            b"TOP SECRET",
            content_type="text/plain",
        )

        response = self.client.post(
            url,
            {
                "domain_id": self.domain.id,
                "url": "https://api.example.com/vuln",
                "summary": "High-level issue summary",
                "files": [file],
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertIn("artifact_sha256", response.data)
        self.assertEqual(response.data["delivery_status"], "pending_build")
