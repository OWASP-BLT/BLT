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
    def test_pipeline_sets_hash_and_deletes_temp_files(self, mock_encrypt):
        # REMOVED: uuid mock - no longer needed since we use mkdtemp

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

        # Verify cleanup: no directories with this issue's prefix should remain
        base = Path(settings.REPORT_TMP_DIR)
        leftover_dirs = list(base.glob(f"issue_{self.issue.id}_*"))
        self.assertEqual(leftover_dirs, [], f"Found leftover temp directories: {leftover_dirs}")

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

    @patch("website.zero_trust_pipeline._encrypt_artifact_for_org")
    def test_pipeline_handles_encryption_failure_marks_issue_failed(self, mock_encrypt):
        upload = SimpleUploadedFile(
            "poc.txt",
            b"SECRET EXPLOIT DATA",
            content_type="text/plain",
        )
        mock_encrypt.side_effect = RuntimeError("encryption failed")
        with self.assertRaises(Exception):
            build_and_deliver_zero_trust_issue(self.issue, [upload])
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.delivery_status, "failed")
        # CharFields with blank=True persist as empty string ("") when unset.
        self.assertFalse(self.issue.artifact_sha256)
        self.assertEqual(self.issue.artifact_sha256, "")
        self.assertFalse(self.issue.encryption_method)
        self.assertEqual(self.issue.encryption_method, "")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    @patch("website.zero_trust_pipeline.EmailMessage.send")
    @patch("website.zero_trust_pipeline._encrypt_artifact_for_org")
    def test_pipeline_handles_email_delivery_failure_marks_issue_failed(
        self,
        mock_encrypt,
        mock_email_send,
    ):
        def fake_encrypt(org_config, input_path, tmp_dir, issue):
            out = Path(tmp_dir) / "report.tar.gz.age"
            out.write_bytes(b"encrypted-content")
            return str(out), "age"

        mock_encrypt.side_effect = fake_encrypt
        mock_email_send.side_effect = RuntimeError("email delivery failed")
        upload = SimpleUploadedFile(
            "poc.txt",
            b"SECRET EXPLOIT DATA",
            content_type="text/plain",
        )
        # Email failure should NOT raise; pipeline records distinct status.
        build_and_deliver_zero_trust_issue(self.issue, [upload])
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.delivery_status, "encryption_success_delivery_failed")
        # Encryption succeeded, so metadata should be present
        self.assertTrue(self.issue.artifact_sha256)
        self.assertEqual(self.issue.encryption_method, "age")

    @patch("website.zero_trust_pipeline._encrypt_artifact_for_org")
    def test_pipeline_handles_invalid_encryption_configuration(self, mock_encrypt):
        # Keep DB config valid; force encrypt helper to raise as if misconfigured.
        upload = SimpleUploadedFile(
            "poc.txt",
            b"SECRET EXPLOIT DATA",
            content_type="text/plain",
        )
        mock_encrypt.side_effect = ValueError("Invalid encryption configuration")
        with self.assertRaises(Exception):
            build_and_deliver_zero_trust_issue(self.issue, [upload])
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.delivery_status, "failed")
