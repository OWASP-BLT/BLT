import datetime
import sys
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from django.utils.timezone import make_aware

from website.leaderboard import update_leaderboard_on_dsr_save
from website.models import DailyStatusReport, UserProfile

User = get_user_model()


class LeaderboardSignalTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.profile = self.user.userprofile
        cache.clear()

    def test_signal_updates_profile_on_dsr_save(self):
        """Test that saving a DSR triggers leaderboard updates"""
        with patch("website.leaderboard.transaction.atomic"):
            with patch.object(UserProfile, "update_streak_and_award_points") as mock_update:
                with patch.object(UserProfile, "calculate_leaderboard_score") as mock_calc:
                    # Reset mocks to ensure clean state
                    mock_update.reset_mock()
                    mock_calc.reset_mock()

                    # Create DSR - this will trigger save() and the signal
                    DailyStatusReport.objects.create(user=self.user, date=timezone.now().date(), goal_accomplished=True)

                    # The signal should have been triggered by save()
                    mock_update.assert_called_once()
                    mock_calc.assert_called_once()

    def test_signal_respects_skip_flag(self):
        """Test that signal skips when flag is set"""
        dsr = DailyStatusReport.objects.create(user=self.user, date=timezone.now().date(), goal_accomplished=True)
        dsr._skip_leaderboard_update = True

        with patch("website.leaderboard.transaction.atomic") as mock_atomic:
            update_leaderboard_on_dsr_save(sender=DailyStatusReport, instance=dsr, created=True)
            mock_atomic.assert_not_called()

    def tearDown(self):
        cache.clear()


class UserProfileLeaderboardScoreTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.user_profile = self.user.userprofile

    def test_leaderboard_score_field_defaults(self):
        """Test that leaderboard score fields have correct defaults"""
        self.assertEqual(self.user_profile.leaderboard_score, Decimal("0"))
        self.assertEqual(self.user_profile.quality_score, Decimal("0"))
        self.assertEqual(self.user_profile.check_in_count, 0)
        self.assertIsNone(self.user_profile.last_score_update)

    @patch("website.models.LeaderboardScoringService.calculate_for_user")
    @patch("website.models.DailyStatusReport.objects")
    @patch("website.models.timezone.now")
    def test_calculate_leaderboard_score_success(self, mock_now, mock_objects, mock_calc):
        """Test successful leaderboard score calculation"""
        # Mock dependencies
        mock_now.return_value = make_aware(datetime.datetime(2023, 10, 1, 12, 0, 0))
        mock_objects.filter.return_value.count.return_value = 42
        mock_calc.return_value = (Decimal("85.50"), {"goals": Decimal("90.00"), "other_metric": Decimal("80.00")})

        # Call the method
        score, breakdown = self.user_profile.calculate_leaderboard_score()

        # Assertions
        self.assertEqual(score, Decimal("85.50"))
        self.assertEqual(breakdown["goals"], Decimal("90.00"))
        self.assertEqual(breakdown["other_metric"], Decimal("80.00"))

        # Verify model fields were updated
        self.user_profile.refresh_from_db()
        self.assertEqual(self.user_profile.leaderboard_score, Decimal("85.50"))
        self.assertEqual(self.user_profile.quality_score, Decimal("90.00"))  # goals score
        self.assertEqual(self.user_profile.check_in_count, 42)
        self.assertEqual(self.user_profile.last_score_update, mock_now.return_value)

        # Verify service calls
        mock_calc.assert_called_once_with(self.user)
        mock_objects.filter.assert_called_once_with(user=self.user)
        mock_objects.filter.return_value.count.assert_called_once()

    @patch("website.models.LeaderboardScoringService.calculate_for_user")
    def test_calculate_leaderboard_score_service_error(self, mock_calculate):
        """Test leaderboard score calculation when service raises an exception"""
        # Mock service to raise exception
        mock_calculate.side_effect = Exception("Service unavailable")

        # Call should raise the exception
        with self.assertRaises(Exception) as context:
            self.user_profile.calculate_leaderboard_score()

        self.assertEqual(str(context.exception), "Service unavailable")

        # Verify fields were not updated
        self.user_profile.refresh_from_db()
        self.assertEqual(self.user_profile.leaderboard_score, Decimal("0"))
        self.assertEqual(self.user_profile.check_in_count, 0)
        self.assertIsNone(self.user_profile.last_score_update)

    @patch("website.models.LeaderboardScoringService.calculate_for_user")
    @patch("website.models.DailyStatusReport.objects")
    def test_calculate_leaderboard_score_save_failure(self, mock_objects, mock_calc):
        """Test behavior when save operation fails"""
        mock_calc.return_value = (Decimal("75.00"), {"goals": Decimal("80.00")})
        mock_objects.filter.return_value.count.return_value = 10

        # Since calculate_leaderboard_score() uses locked_self.save() not self.save(),
        # we need to patch the model's save method
        with patch("website.models.UserProfile.save", side_effect=Exception("Database error")):
            with self.assertRaises(Exception) as context:
                self.user_profile.calculate_leaderboard_score()

            self.assertEqual(str(context.exception), "Database error")

    def test_leaderboard_score_boundary_values(self):
        """Test leaderboard score with boundary values"""
        # Test minimum value
        self.user_profile.leaderboard_score = Decimal("0.00")
        self.user_profile.save()
        self.assertEqual(self.user_profile.leaderboard_score, Decimal("0.00"))

        # Test maximum value
        self.user_profile.leaderboard_score = Decimal("100.00")
        self.user_profile.save()
        self.assertEqual(self.user_profile.leaderboard_score, Decimal("100.00"))

    @patch("website.models.LeaderboardScoringService.calculate_for_user")
    def test_calculate_leaderboard_score_multiple_calls(self, mock_calculate):
        """Test multiple calls to calculate_leaderboard_score"""
        mock_calculate.return_value = (Decimal("80.00"), {"goals": Decimal("85.00")})

        # First call
        self.user_profile.calculate_leaderboard_score()
        self.user_profile.refresh_from_db()
        first_update_time = self.user_profile.last_score_update
        # Second call with different values
        mock_calculate.return_value = (Decimal("90.00"), {"goals": Decimal("95.00")})
        self.user_profile.calculate_leaderboard_score()

        # Verify second update
        self.user_profile.refresh_from_db()
        self.assertEqual(self.user_profile.leaderboard_score, Decimal("90.00"))
        self.assertEqual(self.user_profile.quality_score, Decimal("95.00"))
        self.assertNotEqual(self.user_profile.last_score_update, first_update_time)

    def test_leaderboard_score_ordering(self):
        """Test that leaderboard scores can be used for ordering"""
        # Create multiple user profiles with different scores
        user2 = User.objects.create_user(username="user2", email="user2@example.com")
        profile2 = user2.userprofile
        profile2.leaderboard_score = Decimal("95.00")
        profile2.save()

        user3 = User.objects.create_user(username="user3", email="user3@example.com")
        profile3 = user3.userprofile
        profile3.leaderboard_score = Decimal("87.50")
        profile3.save()

        # Update current profile
        self.user_profile.leaderboard_score = Decimal("92.00")
        self.user_profile.save()

        # Test ordering
        profiles_ordered = UserProfile.objects.order_by("-leaderboard_score")
        self.assertEqual(profiles_ordered[0], profile2)  # 95.00
        self.assertEqual(profiles_ordered[1], self.user_profile)  # 92.00
        self.assertEqual(profiles_ordered[2], profile3)  # 87.50

    @patch("website.models.LeaderboardScoringService.calculate_for_user")
    def test_calculate_leaderboard_score_with_existing_data(self, mock_calculate):
        """Test score calculation when user already has some data"""
        # Set up existing data
        self.user_profile.leaderboard_score = Decimal("50.00")
        self.user_profile.quality_score = Decimal("60.00")
        self.user_profile.check_in_count = 5
        self.user_profile.last_score_update = timezone.now() - timedelta(days=1)
        self.user_profile.save()

        # Mock new calculation
        mock_calculate.return_value = (Decimal("75.00"), {"goals": Decimal("80.00")})

        self.user_profile.calculate_leaderboard_score()

        # Verify fields were updated
        self.user_profile.refresh_from_db()
        self.assertEqual(self.user_profile.leaderboard_score, Decimal("75.00"))
        self.assertEqual(self.user_profile.quality_score, Decimal("80.00"))

    def test_related_models_integration(self):
        """Test integration with related models"""
        # Test that user profile can be accessed from user
        self.assertEqual(self.user.userprofile, self.user_profile)

        # Test that the fields are accessible
        self.user_profile.leaderboard_score = Decimal("88.88")
        self.user_profile.save()

        accessed_profile = User.objects.get(pk=self.user.pk).userprofile
        self.assertEqual(accessed_profile.leaderboard_score, Decimal("88.88"))


class UserProfileLeaderboardIntegrationTest(TestCase):
    """Integration tests focused on leaderboard scoring"""

    def setUp(self):
        self.user = User.objects.create_user(username="integrationuser", email="integration@example.com")
        self.profile = self.user.userprofile

    def test_full_leaderboard_workflow(self):
        """Test complete leaderboard scoring workflow"""
        # Initial state
        self.assertEqual(self.profile.leaderboard_score, Decimal("0"))
        self.assertIsNone(self.profile.last_score_update)

        # Simulate score calculation
        with patch("website.models.LeaderboardScoringService.calculate_for_user") as mock_calc:
            mock_calc.return_value = (Decimal("92.50"), {"goals": Decimal("95.00")})

            score, breakdown = self.profile.calculate_leaderboard_score()

            # Verify results
            self.assertEqual(score, Decimal("92.50"))
            self.assertEqual(breakdown["goals"], Decimal("95.00"))

            # Verify persistent storage
            updated_profile = UserProfile.objects.get(pk=self.profile.pk)
            self.assertEqual(updated_profile.leaderboard_score, Decimal("92.50"))
            self.assertEqual(updated_profile.quality_score, Decimal("95.00"))
            self.assertIsNotNone(updated_profile.last_score_update)


class RecalcLeaderboardsCommandTest(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username="user1", password="pass")
        self.user2 = User.objects.create_user(username="user2", password="pass")

    def test_command_runs_without_errors(self):
        """Test that the command runs without raising exceptions"""
        out = StringIO()
        err = StringIO()
        sys.stdout = out
        sys.stderr = err

        try:
            call_command("recalc_all_leaderboards")
            output = out.getvalue()
            self.assertIn("Recalculating leaderboard scores", output)
            self.assertIn("completed", output.lower())
        finally:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__

    def test_command_handles_errors_gracefully(self):
        """Test command continues when individual users fail"""

        with patch("website.services.leaderboard_scoring.LeaderboardScoringService.calculate_for_user") as mock_calc:
            mock_calc.side_effect = Exception("Test error")
            out = StringIO()
            # Command should complete without raising, despite per-user errors
            call_command("recalc_all_leaderboards", stdout=out)

            # Verify the command attempted to process users
            self.assertGreaterEqual(mock_calc.call_count, 1)
            # Optionally verify error was logged/handled
            output = out.getvalue()
            self.assertIn("completed", output.lower())
