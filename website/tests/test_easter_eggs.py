import hashlib
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from website.models import BaconEarning, EasterEgg, EasterEggDiscovery


class EasterEggModelTest(TestCase):
    """Test Easter Egg model"""

    def setUp(self):
        self.easter_egg = EasterEgg.objects.create(
            name="Test Easter Egg",
            code="test-egg",
            description="A test Easter egg",
            reward_type="bacon",
            reward_amount=5,
            is_active=True,
            max_claims_per_user=1,
        )

    def test_easter_egg_creation(self):
        """Test Easter egg can be created"""
        self.assertEqual(self.easter_egg.name, "Test Easter Egg")
        self.assertEqual(self.easter_egg.code, "test-egg")
        self.assertEqual(self.easter_egg.reward_type, "bacon")
        self.assertEqual(self.easter_egg.reward_amount, 5)
        self.assertTrue(self.easter_egg.is_active)

    def test_easter_egg_str(self):
        """Test Easter egg string representation"""
        self.assertEqual(str(self.easter_egg), "Test Easter Egg (test-egg)")


class EasterEggDiscoveryTest(TestCase):
    """Test Easter Egg discovery functionality"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.easter_egg = EasterEgg.objects.create(
            name="Konami Code",
            code="konami-code",
            description="Classic Konami code Easter egg",
            reward_type="fun",
            reward_amount=0,
            is_active=True,
            max_claims_per_user=1,
        )
        self.bacon_egg = EasterEgg.objects.create(
            name="Secret Bacon",
            code="secret-bacon",
            description="Secret bacon token Easter egg",
            reward_type="bacon",
            reward_amount=10,
            is_active=True,
            max_claims_per_user=1,
        )

    def test_discover_easter_egg_not_authenticated(self):
        """Test discovering Easter egg without authentication"""
        response = self.client.post(
            reverse("discover_easter_egg"), {"code": "konami-code"}
        )
        # Should redirect to login
        self.assertEqual(response.status_code, 302)

    def test_discover_easter_egg_authenticated(self):
        """Test discovering Easter egg while authenticated"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("discover_easter_egg"), {"code": "konami-code"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))
        self.assertIn("Konami Code", data.get("message", ""))

        # Check discovery was recorded
        self.assertTrue(
            EasterEggDiscovery.objects.filter(
                user=self.user, easter_egg=self.easter_egg
            ).exists()
        )

    def test_discover_same_egg_twice(self):
        """Test that user cannot discover the same Easter egg twice"""
        self.client.login(username="testuser", password="testpass123")

        # First discovery
        response1 = self.client.post(
            reverse("discover_easter_egg"), {"code": "konami-code"}
        )
        self.assertEqual(response1.status_code, 200)
        self.assertTrue(response1.json().get("success"))

        # Second discovery attempt
        response2 = self.client.post(
            reverse("discover_easter_egg"), {"code": "konami-code"}
        )
        self.assertEqual(response2.status_code, 400)
        data = response2.json()
        self.assertIn("already discovered", data.get("error", "").lower())

    def test_discover_invalid_easter_egg(self):
        """Test discovering non-existent Easter egg"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("discover_easter_egg"), {"code": "invalid-egg"}
        )
        self.assertEqual(response.status_code, 404)

    def test_discover_inactive_easter_egg(self):
        """Test discovering inactive Easter egg"""
        inactive_egg = EasterEgg.objects.create(
            name="Inactive Egg",
            code="inactive-egg",
            description="Inactive Easter egg",
            reward_type="fun",
            is_active=False,
        )
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("discover_easter_egg"), {"code": "inactive-egg"}
        )
        self.assertEqual(response.status_code, 404)

    def test_bacon_egg_requires_verification(self):
        """Test that bacon Easter egg requires verification token"""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.post(
            reverse("discover_easter_egg"), {"code": "secret-bacon"}
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("Invalid", data.get("error", ""))

    def test_bacon_egg_with_valid_verification(self):
        """Test bacon Easter egg discovery with valid verification token"""
        self.client.login(username="testuser", password="testpass123")

        # Get verification token
        verify_response = self.client.get(
            reverse("get_verification_token"), {"code": "secret-bacon"}
        )
        self.assertEqual(verify_response.status_code, 200)
        token = verify_response.json().get("token")
        self.assertIsNotNone(token)

        # Discover with verification
        response = self.client.post(
            reverse("discover_easter_egg"),
            {"code": "secret-bacon", "verification": token},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data.get("success"))

        # Check bacon earning was created
        bacon_earning = BaconEarning.objects.get(user=self.user)
        self.assertEqual(bacon_earning.tokens_earned, Decimal("10.00"))

    def test_bacon_egg_invalid_verification_token(self):
        """Test bacon Easter egg with invalid verification token"""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.post(
            reverse("discover_easter_egg"),
            {"code": "secret-bacon", "verification": "invalid-token-12345"},
        )
        self.assertEqual(response.status_code, 400)

    def test_rate_limiting(self):
        """Test rate limiting on Easter egg discovery attempts"""
        self.client.login(username="testuser", password="testpass123")

        # Make 10 failed attempts (max allowed per hour)
        for i in range(10):
            self.client.post(
                reverse("discover_easter_egg"), {"code": f"invalid-egg-{i}"}
            )

        # 11th attempt should be rate limited
        response = self.client.post(
            reverse("discover_easter_egg"), {"code": "konami-code"}
        )
        self.assertEqual(response.status_code, 429)
        data = response.json()
        self.assertIn("Too many attempts", data.get("error", ""))

    def test_daily_bacon_limit(self):
        """Test that users can only earn bacon tokens once per day"""
        self.client.login(username="testuser", password="testpass123")

        # Get verification token
        verify_response = self.client.get(
            reverse("get_verification_token"), {"code": "secret-bacon"}
        )
        token = verify_response.json().get("token")

        # First bacon discovery
        response1 = self.client.post(
            reverse("discover_easter_egg"),
            {"code": "secret-bacon", "verification": token},
        )
        self.assertEqual(response1.status_code, 200)

        # Create another bacon Easter egg
        another_bacon_egg = EasterEgg.objects.create(
            name="Another Bacon",
            code="another-bacon",
            description="Another bacon Easter egg",
            reward_type="bacon",
            reward_amount=5,
            is_active=True,
        )

        # Get verification token for second egg
        verify_response2 = self.client.get(
            reverse("get_verification_token"), {"code": "another-bacon"}
        )
        token2 = verify_response2.json().get("token")

        # Second bacon discovery on same day should fail
        response2 = self.client.post(
            reverse("discover_easter_egg"),
            {"code": "another-bacon", "verification": token2},
        )
        self.assertEqual(response2.status_code, 400)
        data = response2.json()
        self.assertIn("already earned bacon", data.get("error", "").lower())

    def test_easter_egg_discovery_records_metadata(self):
        """Test that discovery records IP and user agent"""
        self.client.login(username="testuser", password="testpass123")

        response = self.client.post(
            reverse("discover_easter_egg"),
            {"code": "konami-code"},
            REMOTE_ADDR="127.0.0.1",
            HTTP_USER_AGENT="TestBrowser/1.0",
        )
        self.assertEqual(response.status_code, 200)

        discovery = EasterEggDiscovery.objects.get(
            user=self.user, easter_egg=self.easter_egg
        )
        self.assertEqual(discovery.ip_address, "127.0.0.1")
        self.assertEqual(discovery.user_agent, "TestBrowser/1.0")


class EasterEggSecurityTest(TestCase):
    """Test security features of Easter egg system"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.bacon_egg = EasterEgg.objects.create(
            name="Secret Bacon",
            code="secret-bacon",
            description="Secret bacon token Easter egg",
            reward_type="bacon",
            reward_amount=10,
            is_active=True,
        )

    def test_csrf_protection(self):
        """Test that CSRF protection is enforced"""
        self.client.login(username="testuser", password="testpass123")
        # Django test client handles CSRF automatically, but we can test without it
        self.client.handler.enforce_csrf_checks = True

        response = self.client.post(
            reverse("discover_easter_egg"), {"code": "secret-bacon"}
        )
        # Should fail without CSRF token
        self.assertEqual(response.status_code, 403)

    def test_verification_token_cannot_be_reused(self):
        """Test that verification tokens are tied to current date"""
        self.client.login(username="testuser", password="testpass123")

        # Get verification token
        verify_response = self.client.get(
            reverse("get_verification_token"), {"code": "secret-bacon"}
        )
        token = verify_response.json().get("token")

        # Use it successfully
        response = self.client.post(
            reverse("discover_easter_egg"),
            {"code": "secret-bacon", "verification": token},
        )
        self.assertEqual(response.status_code, 200)

        # Token should not work again (already discovered)
        response2 = self.client.post(
            reverse("discover_easter_egg"),
            {"code": "secret-bacon", "verification": token},
        )
        self.assertEqual(response2.status_code, 400)
