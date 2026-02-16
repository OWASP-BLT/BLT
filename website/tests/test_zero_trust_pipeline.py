from django.test import TestCase

from website.zero_trust_pipeline import _validate_age_recipient, _validate_pgp_fingerprint


class ValidationFunctionTests(TestCase):
    """Test security-critical validation functions."""

    def test_validate_age_recipient_valid(self):
        """Test valid age recipients."""
        # Valid age1 format (age1 + 58 chars)
        self.assertTrue(_validate_age_recipient("age1" + "q" * 58))

        # Valid SSH keys with sufficiently long base64 portions
        self.assertTrue(
            _validate_age_recipient(
                "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAabcdefghijklmnopqrstuvwxyz"
            )
        )
        self.assertTrue(
            _validate_age_recipient(
                "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCsabcdefghijklmnopqrstuvwxyz"
            )
        )

    def test_validate_age_recipient_invalid(self):
        """Test invalid age recipients."""
        # Wrong length
        self.assertFalse(_validate_age_recipient("age1" + "q" * 50))
        self.assertFalse(_validate_age_recipient("age1" + "q" * 70))

        # Wrong prefix
        self.assertFalse(_validate_age_recipient("age2" + "q" * 58))

        # Invalid characters
        self.assertFalse(_validate_age_recipient("age1" + "Q" * 58))  # uppercase not allowed
        self.assertFalse(_validate_age_recipient("age1" + "!" * 58))

        # Empty
        self.assertFalse(_validate_age_recipient(""))

    def test_validate_pgp_fingerprint_valid(self):
        """Test valid PGP fingerprints."""
        # SHA-1 (40 hex chars)
        self.assertTrue(_validate_pgp_fingerprint("A" * 40))
        self.assertTrue(_validate_pgp_fingerprint("1234567890ABCDEF" * 2 + "12345678"))

        # SHA-256 (64 hex chars)
        self.assertTrue(_validate_pgp_fingerprint("B" * 64))
        self.assertTrue(_validate_pgp_fingerprint("1234567890abcdef" * 4))

    def test_validate_pgp_fingerprint_invalid(self):
        """Test invalid PGP fingerprints."""
        # Wrong length
        self.assertFalse(_validate_pgp_fingerprint("A" * 39))
        self.assertFalse(_validate_pgp_fingerprint("A" * 41))
        self.assertFalse(_validate_pgp_fingerprint("A" * 63))
        self.assertFalse(_validate_pgp_fingerprint("A" * 65))

        # Non-hex characters
        self.assertFalse(_validate_pgp_fingerprint("G" * 40))
        self.assertFalse(_validate_pgp_fingerprint("!" * 64))

        # Spaces or dashes (not allowed)
        self.assertFalse(_validate_pgp_fingerprint("AAAA BBBB CCCC DDDD " * 2))
        self.assertFalse(_validate_pgp_fingerprint("A" * 39 + " "))

        # Empty
        self.assertFalse(_validate_pgp_fingerprint(""))
