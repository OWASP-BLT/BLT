from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.db import transaction
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone


class UserProfileUpdateTest(TestCase):
    def setUp(self):
        # Create test user
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        # UserProfile is created automatically by signal
        self.client.login(username="testuser", password="testpass123")

    def test_update_profile_with_valid_bch_address(self):
        """Test updating user profile with a valid BCH address"""
        # Valid BCH address starts with 'bitcoincash:'
        valid_bch_address = "bitcoincash:qr5yccf7j4dpjekyz3vpawgaarl352n7yv5d5mtzzc"

        # Update the profile with valid BCH address
        data = {
            "email": self.user.email,
            "bch_address": valid_bch_address,
            "description": "Test description",
            "issues_hidden": False,
            "btc_address": "",
            "eth_address": "",
            "x_username": "",
            "linkedin_url": "",
            "website_url": "",
            "github_url": "",
            "role": "",
            "discounted_hourly_rate": 0,
        }

        response = self.client.post(reverse("profile_edit"), data, follow=True)

        # Check if we were redirected (success case)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse("profile", kwargs={"slug": self.user.username}))

        # Verify the BCH address was updated
        self.user.userprofile.refresh_from_db()
        self.assertEqual(self.user.userprofile.bch_address, valid_bch_address)

    def test_update_profile_with_invalid_bch_address(self):
        """Test updating user profile with an invalid BCH address"""
        # Invalid BCH address doesn't start with 'bitcoincash:'
        invalid_bch_address = "qr5yccf7j4dpjekyz3vpawgaarl352n7yv5d5mtzzc"

        # Update the profile with invalid BCH address
        data = {
            "email": self.user.email,
            "bch_address": invalid_bch_address,
            "description": "Test description",
            "issues_hidden": False,
            "btc_address": "",
            "eth_address": "",
            "x_username": "",
            "linkedin_url": "",
            "website_url": "",
            "github_url": "",
            "role": "",
            "discounted_hourly_rate": 0,
        }

        response = self.client.post(reverse("profile_edit"), data)

        # Should stay on the same page with errors
        self.assertEqual(response.status_code, 200)

        # Check for form errors
        self.assertTrue(response.context["form"].errors)
        self.assertIn("bch_address", response.context["form"].errors)

        # Verify the BCH address was not updated
        self.user.userprofile.refresh_from_db()
        self.assertNotEqual(self.user.userprofile.bch_address, invalid_bch_address)

    def test_update_email_address(self):
        """Test updating user profile with a new email address"""
        new_email = "newemail@example.com"

        # Update the profile with new email
        data = {
            "email": new_email,
            "description": "Test description",
            "issues_hidden": False,
            "bch_address": "",
            "btc_address": "",
            "eth_address": "",
            "x_username": "",
            "linkedin_url": "",
            "website_url": "",
            "github_url": "",
            "role": "",
            "discounted_hourly_rate": 0,
        }

        response = self.client.post(reverse("profile_edit"), data, follow=True)

        # Check if we were redirected (success case)
        self.assertEqual(response.status_code, 200)
        self.assertRedirects(response, reverse("profile", kwargs={"slug": self.user.username}))

        # The current implementation doesn't update the User model's email
        # It only validates that the email is unique
        # So we just verify that the form was submitted successfully
        messages_list = [m.message for m in response.context["messages"]]
        self.assertTrue(
            any(m.startswith("A verification link has been sent to your new email.") for m in messages_list)
        )

        # Verify that the email was NOT updated (remains original until verification)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "test@example.com")

    def test_update_email_to_existing_email(self):
        """Test updating to an email that's already in use by another user"""
        # Create another user with a different email
        other_user = User.objects.create_user(username="otheruser", email="other@example.com", password="testpass123")

        # Try to update the first user's email to match the second user's
        data = {
            "email": other_user.email,
            "description": "Test description",
            "issues_hidden": False,
            "bch_address": "",
            "btc_address": "",
            "eth_address": "",
            "x_username": "",
            "linkedin_url": "",
            "website_url": "",
            "github_url": "",
            "role": "",
            "discounted_hourly_rate": 0,
        }

        response = self.client.post(reverse("profile_edit"), data)

        # Should stay on the same page with errors
        self.assertEqual(response.status_code, 200)

        # Check for form errors
        self.assertIn("email", response.context["form"].errors)
        self.assertIn("This email is already in use", str(response.context["form"].errors["email"]))

        # Verify the email was not updated
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "test@example.com")


class UserProfileVerifierTest(TestCase):
    def setUp(self):
        # Create test users
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.verifier_user = User.objects.create_user(
            username="verifieruser", email="verifier@example.com", password="testpass123"
        )
        # UserProfile is created automatically by signal

    def test_default_is_verifier_false(self):
        """Test that new users are not verifiers by default"""
        self.assertFalse(self.user.userprofile.is_verifier)

    def test_set_user_as_verifier(self):
        """Test setting a user as a verifier"""
        self.user.userprofile.is_verifier = True
        self.user.userprofile.save()
        self.user.userprofile.refresh_from_db()
        self.assertTrue(self.user.userprofile.is_verifier)

    def test_check_verifier_permission_method(self):
        """Test the check_verifier_permission method"""
        # Test with non-verifier user
        self.assertFalse(self.user.userprofile.check_verifier_permission())

        # Set user as verifier
        self.user.userprofile.is_verifier = True
        self.user.userprofile.save()

        # Test with verifier user
        self.assertTrue(self.user.userprofile.check_verifier_permission())

    def test_verifier_permission_independent_of_role(self):
        """Test that verifier permission is independent of role field"""
        # Set a role and verify permission
        self.user.userprofile.role = "Developer"
        self.user.userprofile.is_verifier = True
        self.user.userprofile.save()
        self.user.userprofile.refresh_from_db()

        self.assertEqual(self.user.userprofile.role, "Developer")
        self.assertTrue(self.user.userprofile.is_verifier)

    def test_remove_verifier_permission(self):
        """Test removing verifier permission from a user"""
        # First set as verifier
        self.user.userprofile.is_verifier = True
        self.user.userprofile.save()
        self.assertTrue(self.user.userprofile.is_verifier)

        # Then remove verifier permission
        self.user.userprofile.is_verifier = False
        self.user.userprofile.save()
        self.user.userprofile.refresh_from_db()
        self.assertFalse(self.user.userprofile.is_verifier)


class UserProfileVisitCounterTest(TestCase):
    def setUp(self):
        """Create test user with profile"""
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        # UserProfile is created automatically by signal
        self.profile = self.user.userprofile

    def test_update_visit_counter_first_visit(self):
        """Test that first visit increments both counters"""
        initial_visit_count = self.profile.visit_count
        initial_daily_count = self.profile.daily_visit_count

        self.profile.update_visit_counter()
        self.profile.refresh_from_db()

        self.assertEqual(self.profile.visit_count, initial_visit_count + 1)
        self.assertEqual(self.profile.daily_visit_count, initial_daily_count + 1)
        self.assertIsNotNone(self.profile.last_visit_day)

    def test_update_visit_counter_same_day(self):
        """Test that multiple visits on same day only increment general counter"""
        # First visit
        self.profile.update_visit_counter()
        self.profile.refresh_from_db()
        first_daily_count = self.profile.daily_visit_count
        first_visit_count = self.profile.visit_count

        # Second visit on same day
        self.profile.update_visit_counter()
        self.profile.refresh_from_db()

        # Daily count should stay the same
        self.assertEqual(self.profile.daily_visit_count, first_daily_count)
        # General visit count should increment
        self.assertEqual(self.profile.visit_count, first_visit_count + 1)

    def test_update_visit_counter_different_days(self):
        """Test that visits on different days increment both counters"""
        # First visit
        self.profile.update_visit_counter()
        self.profile.refresh_from_db()
        first_daily_count = self.profile.daily_visit_count
        first_visit_count = self.profile.visit_count

        # Manually set the last_visit_day to yesterday to simulate a different day visit
        yesterday = timezone.now().date() - timedelta(days=1)
        self.profile.last_visit_day = yesterday
        self.profile.save()

        # Visit on current day (which is different from yesterday)
        self.profile.update_visit_counter()
        self.profile.refresh_from_db()

        # Both counters should increment since it's a different day
        self.assertEqual(self.profile.daily_visit_count, first_daily_count + 1)
        self.assertEqual(self.profile.visit_count, first_visit_count + 1)
        # Last visit day should be updated to today
        self.assertEqual(self.profile.last_visit_day, timezone.now().date())

    def test_update_visit_counter_atomic_operations(self):
        """Test that update_visit_counter uses atomic operations to prevent transaction errors"""
        # This test ensures the method works within a transaction without calling save()
        # which would cause TransactionManagementError in certain scenarios

        initial_visit_count = self.profile.visit_count

        # Test that the method works within a transaction
        with transaction.atomic():
            # Mock the save method to ensure it's not called
            with patch.object(self.profile, "save") as mock_save:
                self.profile.update_visit_counter()
                # save() should not be called - we use atomic QuerySet.update() instead
                mock_save.assert_not_called()

        # Verify the counters were still updated using atomic database operations
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.visit_count, initial_visit_count + 1)

    def test_update_visit_counter_no_transaction_error(self):
        """Test that update_visit_counter doesn't raise TransactionManagementError"""

        # This test ensures the method doesn't raise TransactionManagementError
        # when called multiple times within the same transaction
        try:
            with transaction.atomic():
                self.profile.update_visit_counter()
                self.profile.update_visit_counter()
            # If we get here, no TransactionManagementError was raised
            success = True
        except transaction.TransactionManagementError:
            success = False

        self.assertTrue(success, "update_visit_counter raised TransactionManagementError")
