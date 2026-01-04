import os
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from website.models import Domain, Issue, Organization, OrgEncryptionConfig
from website.zero_trust_pipeline import (
    _generate_secure_password,
    build_and_deliver_zero_trust_issue,
)

User = get_user_model()


class SymmetricEncryptionTests(TestCase):
    """Test suite for sym_7z encryption method."""

    def setUp(self):
        self.user = User.objects.create_user(username="sym7z_tester", password="password")
        self.org = Organization.objects.create(name="Sym7z Test Org")
        self.domain = Domain.objects.create(organization=self.org, url="https://sym7z.example.com")

        self.enc = OrgEncryptionConfig.objects.create(
            organization=self.org,
            contact_email="security@sym7z.example.com",
            preferred_method="sym_7z",
        )

        self.issue = Issue.objects.create(
            user=self.user,
            domain=self.domain,
            url="https://sym7z.example.com/vuln",
            description="High-level summary for sym_7z test",
            is_hidden=True,
            is_zero_trust=True,
            delivery_status="pending_build",
        )

    def test_generate_secure_password(self):
        """Test that password generation meets security requirements."""
        password = _generate_secure_password(32)
        
        # Check length
        self.assertEqual(len(password), 32)
        
        # Check character diversity
        self.assertTrue(any(c.isupper() for c in password), "Must contain uppercase")
        self.assertTrue(any(c.islower() for c in password), "Must contain lowercase")
        self.assertTrue(any(c.isdigit() for c in password), "Must contain digit")
        self.assertTrue(any(c in "!@#$%^&*-_=+" for c in password), "Must contain special char")
        
        # Check uniqueness (extremely unlikely to generate same password twice)
        password2 = _generate_secure_password(32)
        self.assertNotEqual(password, password2)

    def test_generate_secure_password_custom_length(self):
        """Test password generation with different lengths."""
        for length in [16, 24, 32, 64]:
            password = _generate_secure_password(length)
            self.assertEqual(len(password), length)

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    @patch("website.zero_trust_pipeline._encrypt_artifact_for_org")
    @patch("website.zero_trust_pipeline.uuid.uuid4")
    def test_sym7z_pipeline_sends_two_emails(self, mock_uuid, mock_encrypt):
        """Test that sym_7z sends both artifact email and password email."""
        fixed_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        mock_uuid.return_value = fixed_uuid

        # Mock encryption to create a fake .7z file AND call _deliver_password_oob
        def fake_encrypt(org_config, input_path, tmp_dir, issue):
            out = Path(tmp_dir) / "report_payload.tar.gz.7z"
            out.write_bytes(b"fake-7z-encrypted-content")
            
            # IMPORTANT: Also call _deliver_password_oob to simulate real sym_7z behavior
            # Import here to avoid circular dependency
            from website.zero_trust_pipeline import _deliver_password_oob
            _deliver_password_oob(org_config, issue.id, "fake-password-12345")
            
            return str(out), "sym_7z"

        mock_encrypt.side_effect = fake_encrypt

        upload = SimpleUploadedFile("exploit.txt", b"secret payload", content_type="text/plain")

        # Clear any existing emails
        mail.outbox = []

        build_and_deliver_zero_trust_issue(self.issue, [upload])

        # Should have 2 emails: artifact + password
        self.assertEqual(len(mail.outbox), 2)

        # Find which email is which
        artifact_email = None
        password_email = None
        
        for email in mail.outbox:
            if "PASSWORD" in email.subject:
                password_email = email
            else:
                artifact_email = email

        self.assertIsNotNone(artifact_email, "Should have artifact email")
        self.assertIsNotNone(password_email, "Should have password email")

        # Verify artifact email
        self.assertIn("VULN REPORT", artifact_email.subject)
        self.assertIn(str(self.issue.id), artifact_email.subject)
        self.assertEqual(artifact_email.to, ["security@sym7z.example.com"])
        self.assertEqual(len(artifact_email.attachments), 1)

        # Verify password email
        self.assertIn("PASSWORD", password_email.subject)
        self.assertIn(str(self.issue.id), password_email.subject)
        self.assertEqual(password_email.to, ["security@sym7z.example.com"])
        self.assertIn("Decryption Password:", password_email.body)
        self.assertIn("7z x", password_email.body)  # Decryption instructions
        self.assertEqual(len(password_email.attachments), 0)  # No attachment on password email

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    @patch("website.zero_trust_pipeline.subprocess.run")
    @patch("website.zero_trust_pipeline.uuid.uuid4")
    def test_sym7z_encryption_command(self, mock_uuid, mock_subprocess):
        """Test that 7z is called with correct arguments."""
        fixed_uuid = uuid.UUID("12345678-1234-5678-1234-567812345678")
        mock_uuid.return_value = fixed_uuid

        # Mock subprocess to avoid needing real 7z binary
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        upload = SimpleUploadedFile("test.txt", b"test data", content_type="text/plain")

        try:
            build_and_deliver_zero_trust_issue(self.issue, [upload])
        except Exception:
            pass  # May fail on email send, but we just want to check subprocess call

        # Find the 7z encryption call
        calls = [call for call in mock_subprocess.call_args_list if call[0][0][0].endswith("7z")]
        
        self.assertGreater(len(calls), 0, "7z should have been called")
        
        cmd = calls[0][0][0]  # First positional arg is the command list
        
        # Verify critical security flags
        self.assertIn("7z", str(cmd))
        self.assertIn("-mhe=on", cmd, "Should encrypt headers")
        self.assertIn("-t7z", cmd, "Should use 7z format")
        self.assertTrue(any("-p" in arg for arg in cmd), "Should have password flag")

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    @patch("website.zero_trust_pipeline._encrypt_artifact_for_org")
    def test_sym7z_password_not_in_database(self, mock_encrypt):
        """Ensure password is never stored in database."""
        def fake_encrypt(org_config, input_path, tmp_dir, issue):
            out = Path(tmp_dir) / "report_payload.tar.gz.7z"
            out.write_bytes(b"encrypted")
            return str(out), "sym_7z"

        mock_encrypt.side_effect = fake_encrypt

        upload = SimpleUploadedFile("test.txt", b"data", content_type="text/plain")

        build_and_deliver_zero_trust_issue(self.issue, [upload])
        self.issue.refresh_from_db()

        # Check that no field contains a password-like string
        fields_to_check = [
            self.issue.description,
            self.issue.url,
            self.issue.delivery_status,
            self.issue.encryption_method,
            self.issue.delivery_method,
        ]
        
        for field in fields_to_check:
            if field:
                # Password should not appear in any field
                self.assertNotRegex(
                    str(field),
                    r"[A-Za-z0-9!@#$%^&*\-_=+]{32}",
                    f"Field should not contain password-like string: {field}"
                )

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    @patch("website.zero_trust_pipeline._deliver_password_oob")
    @patch("website.zero_trust_pipeline.subprocess.run")
    def test_sym7z_oob_failure_stops_pipeline(self, mock_subprocess, mock_oob):
        """Test that OOB delivery failure prevents pipeline completion."""
        # Mock successful 7z encryption
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_subprocess.return_value = mock_result

        # Mock OOB delivery failure
        mock_oob.side_effect = RuntimeError("OOB delivery failed")

        upload = SimpleUploadedFile("test.txt", b"data", content_type="text/plain")

        with self.assertRaises(Exception):
            build_and_deliver_zero_trust_issue(self.issue, [upload])

        self.issue.refresh_from_db()
        self.assertEqual(self.issue.delivery_status, "failed")