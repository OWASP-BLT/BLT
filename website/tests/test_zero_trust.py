import uuid
from pathlib import Path
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from website.models import Domain, Issue, Organization, OrgEncryptionConfig
from website.zero_trust_pipeline import build_and_deliver_zero_trust_issue

User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ZeroTrustPipelineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="password")

        self.org = Organization.objects.create(name="Test Org")

        self.domain = Domain.objects.create(organization=self.org, url="https://example.com")

        # FIXED: Use "age" instead of "sym_7z" (which is now disabled)
        # We mock _encrypt_artifact_for_org anyway, so we don't need real age binary
        self.enc = OrgEncryptionConfig.objects.create(
            organization=self.org,
            contact_email="security@example.com",
            preferred_method="age",
            age_recipient="age1" + "q" * 58,  # Valid format age recipient
        )

        self.issue = Issue.objects.create(
            user=self.user,
            domain=self.domain,
            url="https://example.com/vuln",
            description="High-level summary only",
            is_hidden=True,
            is_zero_trust=True,
            delivery_status="pending_build",
        )

    @patch("website.zero_trust_pipeline._encrypt_artifact_for_org")
    @patch("website.zero_trust_pipeline.uuid.uuid4")
    def test_pipeline_sets_hash_and_deletes_temp_files(self, mock_uuid, mock_encrypt):
        fixed_uuid = uuid.UUID("12345678123456781234567812345678")
        mock_uuid.return_value = fixed_uuid

        # Let the pipeline create the temp dir; do NOT pre-create it.

        def fake_encrypt(org_config, input_path, tmp_dir, issue):
            out = Path(tmp_dir) / "report.tar.gz.age"
            out.write_bytes(b"encrypted-content")
            return str(out), "age"

        mock_encrypt.side_effect = fake_encrypt

        upload = SimpleUploadedFile("poc.txt", b"secret data", content_type="text/plain")

        build_and_deliver_zero_trust_issue(self.issue, [upload])
        self.issue.refresh_from_db()

        self.assertTrue(self.issue.is_zero_trust)
        self.assertIsNotNone(self.issue.artifact_sha256)
        self.assertEqual(self.issue.encryption_method, "age")

        issue_tmp_dir = Path(settings.REPORT_TMP_DIR) / str(fixed_uuid)
        self.assertFalse(issue_tmp_dir.exists())

    def test_pipeline_fails_cleanly_without_org_config(self):
        self.enc.delete()

        upload = SimpleUploadedFile(
            "poc.txt",
            b"SECRET EXPLOIT DATA",
            content_type="text/plain",
        )

        with self.assertRaises(Exception):
            build_and_deliver_zero_trust_issue(self.issue, [upload])

        self.issue.refresh_from_db()
        self.assertEqual(self.issue.delivery_status, "failed")

@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
@patch("website.zero_trust_pipeline._encrypt_artifact_for_org")
@patch("website.zero_trust_pipeline.uuid.uuid4")
def test_pipeline_works_with_sym7z_config(self, mock_uuid, mock_encrypt):
    """Test that pipeline works when org uses sym_7z."""
    # Update org config to use sym_7z
    self.enc.preferred_method = "sym_7z"
    self.enc.age_recipient = ""  # Clear age recipient
    self.enc.save()
    
    fixed_uuid = uuid.UUID("87654321-4321-8765-4321-876543218765")
    mock_uuid.return_value = fixed_uuid

    def fake_encrypt(org_config, input_path, tmp_dir, issue):
        out = Path(tmp_dir) / "report.tar.gz.7z"
        out.write_bytes(b"7z-encrypted-content")
        return str(out), "sym_7z"

    mock_encrypt.side_effect = fake_encrypt

    upload = SimpleUploadedFile("poc.txt", b"secret exploit", content_type="text/plain")

    build_and_deliver_zero_trust_issue(self.issue, [upload])
    self.issue.refresh_from_db()

    self.assertTrue(self.issue.is_zero_trust)
    self.assertIsNotNone(self.issue.artifact_sha256)
    self.assertEqual(self.issue.encryption_method, "sym_7z")
    self.assertEqual(self.issue.delivery_status, "delivered")