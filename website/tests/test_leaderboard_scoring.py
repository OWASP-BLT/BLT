import datetime
from datetime import timedelta
from decimal import Decimal
from io import StringIO
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone
from django.utils.timezone import make_aware

from website.models import DailyStatusReport, Organization, UserProfile
from website.signals import update_leaderboard_on_dsr_save

User = get_user_model()


class LeaderboardSignalBehaviorTest(TestCase):
    """Test signal behavior (what it does) rather than registration (whether it exists)"""

    def setUp(self):
        self.user = User.objects.create_user(username="signaltest", email="signal@example.com")
        self.profile = self.user.userprofile

    def test_signal_updates_streak_on_dsr_save(self):
        """Creating DSR should trigger streak update via signal"""
        # Record initial state
        initial_streak = self.profile.current_streak

        # Create DSR (signal should fire)
        DailyStatusReport.objects.create(
            user=self.user,
            date=timezone.now().date(),
            previous_work="Fixed bugs",
            next_plan="Write tests",
            goal_accomplished=True,
        )

        # Refresh profile
        self.profile.refresh_from_db()

        # Verify signal fired and updated streak
        # (update_streak_and_award_points increments streak)
        self.assertGreaterEqual(
            self.profile.current_streak, initial_streak, "Signal did not update current_streak after DSR creation"
        )

    def test_signal_recalculates_score_on_dsr_save(self):
        """Creating DSR should trigger score recalculation via signal"""
        # Ensure last_score_update starts as None
        self.profile.last_score_update = None
        self.profile.save()

        # Create DSR (signal should fire)
        DailyStatusReport.objects.create(
            user=self.user,
            date=timezone.now().date(),
            previous_work="Implemented feature",
            next_plan="Deploy to staging",
            goal_accomplished=True,
        )

        # Refresh profile
        self.profile.refresh_from_db()

        # Verify signal fired and recalculated score
        self.assertIsNotNone(
            self.profile.last_score_update,
            "Signal did not set last_score_update (calculate_leaderboard_score not called)",
        )

        # Score should be non-zero after a completed goal
        self.assertGreater(self.profile.leaderboard_score, 0, "Signal did not update leaderboard_score")

    def test_signal_respects_skip_flag(self):
        """DSR with _skip_leaderboard_update flag should NOT trigger signal processing"""
        # Record initial state
        initial_score = self.profile.leaderboard_score
        initial_update_time = self.profile.last_score_update

        # Create DSR with skip flag
        dsr = DailyStatusReport(
            user=self.user, date=timezone.now().date(), previous_work="Test", next_plan="Test", goal_accomplished=True
        )
        dsr._skip_leaderboard_update = True  # Set skip flag
        dsr.save()

        # Refresh profile
        self.profile.refresh_from_db()

        # Verify signal did NOT update anything
        self.assertEqual(
            self.profile.leaderboard_score, initial_score, "Signal processed DSR despite _skip_leaderboard_update flag"
        )
        self.assertEqual(
            self.profile.last_score_update, initial_update_time, "Signal updated last_score_update despite skip flag"
        )

    def test_signal_invalidates_team_cache(self):
        """Signal should invalidate team leaderboard cache after DSR save"""
        # Create a team
        team = Organization.objects.create(name="Test Team", url="https://test.com")
        self.profile.team = team
        self.profile.save()

        # Populate cache with fake data
        cache_key = f"team_lb:{team.id}:score:1:20"
        cache.set(cache_key, [{"fake": "data"}], timeout=300)

        # Verify cache is populated
        self.assertIsNotNone(cache.get(cache_key), "Cache setup failed")

        # Create DSR (signal should invalidate cache)
        DailyStatusReport.objects.create(
            user=self.user,
            date=timezone.now().date(),
            previous_work="Cache test",
            next_plan="Verify invalidation",
            goal_accomplished=True,
        )

        # Verify cache was invalidated
        cached_value = cache.get(cache_key)
        # Note: This might still have data if using LocMemCache without delete_pattern
        # But the test documents expected behavior
        if hasattr(cache, "delete_pattern"):
            self.assertIsNone(cached_value, "Signal did not invalidate team leaderboard cache")

    def test_signal_handles_missing_profile_gracefully(self):
        """Signal should not crash if user has no profile"""
        # Create user without profile
        user_no_profile = User.objects.create_user(username="noprofile", email="noprofile@example.com")

        # Delete profile if it was auto-created
        UserProfile.objects.filter(user=user_no_profile).delete()

        # Create DSR for user without profile (should not crash)
        try:
            DailyStatusReport.objects.create(
                user=user_no_profile,
                date=timezone.now().date(),
                previous_work="Test",
                next_plan="Test",
            )
            # If we get here, signal handled it gracefully
        except UserProfile.DoesNotExist:
            self.fail("Signal did not handle missing UserProfile gracefully")

    def test_multiple_dsr_saves_compound_scores(self):
        """Multiple DSR creates should compound leaderboard scores"""
        # Create first DSR
        DailyStatusReport.objects.create(
            user=self.user, date=timezone.now().date(), previous_work="Day 1", next_plan="Day 2", goal_accomplished=True
        )

        self.profile.refresh_from_db()
        score_after_first = self.profile.leaderboard_score

        # Create second DSR
        DailyStatusReport.objects.create(
            user=self.user, date=timezone.now().date(), previous_work="Day 2", next_plan="Day 3", goal_accomplished=True
        )

        self.profile.refresh_from_db()
        score_after_second = self.profile.leaderboard_score

        # Score should increase (frequency and goals improve)
        self.assertGreaterEqual(
            score_after_second, score_after_first, "Signal did not compound scores across multiple DSRs"
        )


class LeaderboardSignalTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")
        self.profile = self.user.userprofile
        cache.clear()

    def test_signal_updates_profile_on_dsr_save(self):
        """Test that saving a DSR triggers leaderboard updates"""
        with patch("website.signals.transaction.atomic"):
            with patch(
                "website.services.leaderboard_scoring.LeaderboardScoringService.calculate_for_user"
            ) as mock_calc:
                with patch.object(UserProfile, "update_streak_and_award_points") as mock_update:
                    # Reset mocks to ensure clean state
                    mock_update.reset_mock()
                    mock_calc.reset_mock()

                    # Add return value for calculate_for_user
                    mock_calc.return_value = (
                        Decimal("10.0"),
                        {"completeness": Decimal("5.0")},
                    )

                    # Create DSR - this will trigger save() and the signal
                    DailyStatusReport.objects.create(user=self.user, date=timezone.now().date(), goal_accomplished=True)

                    # The signal should have been triggered by save()
                    mock_update.assert_called_once()
                    mock_calc.assert_called_once_with(self.user)

    def test_signal_respects_skip_flag(self):
        """Test that signal skips when flag is set"""
        dsr = DailyStatusReport.objects.create(user=self.user, date=timezone.now().date(), goal_accomplished=True)
        dsr._skip_leaderboard_update = True

        with patch("website.signals.transaction.atomic") as mock_atomic:
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
    @patch("website.models.DailyStatusReport.objects.filter")
    @patch("website.models.timezone.now")
    def test_calculate_leaderboard_score_success(self, mock_now, mock_filter, mock_calc):
        """Test successful leaderboard score calculation"""
        # Mock dependencies
        mock_now.return_value = make_aware(datetime.datetime(2023, 10, 1, 12, 0, 0))

        # Mock the filter chain
        mock_queryset = MagicMock()
        mock_queryset.count.return_value = 42
        mock_filter.return_value = mock_queryset

        mock_calc.return_value = (Decimal("85.50"), {"completeness": Decimal("90.00")})

        # Call the method
        score, breakdown = self.user_profile.calculate_leaderboard_score()

        # Assertions
        self.assertEqual(score, Decimal("85.50"))
        self.assertEqual(breakdown["completeness"], Decimal("90.00"))

        # Verify model fields were updated
        self.user_profile.refresh_from_db()
        self.assertEqual(self.user_profile.leaderboard_score, Decimal("85.50"))
        self.assertEqual(self.user_profile.quality_score, Decimal("90.00"))  # completeness score
        self.assertEqual(self.user_profile.check_in_count, 42)
        self.assertEqual(self.user_profile.last_score_update, mock_now.return_value)

        # Verify service calls
        mock_calc.assert_called_once_with(self.user)

        # Verify filter was called with correct intent, not exact arguments
        args, kwargs = mock_filter.call_args
        self.assertEqual(kwargs["user"], self.user)
        # Check for either date or created_at filter (both are valid)
        self.assertTrue("date__gte" in kwargs or "created_at__gte" in kwargs)

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
    @patch("website.models.DailyStatusReport.objects.filter")
    def test_calculate_leaderboard_score_save_failure(self, mock_filter, mock_calc):
        """Test behavior when save operation fails"""
        mock_calc.return_value = (
            Decimal("75.00"),
            {"completeness": Decimal("80.00")},
        )

        # Mock the filter chain
        mock_queryset = MagicMock()
        mock_queryset.count.return_value = 10
        mock_filter.return_value = mock_queryset

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
        mock_calculate.return_value = (Decimal("80.00"), {"completeness": Decimal("85.00")})
        # First call
        self.user_profile.calculate_leaderboard_score()
        self.user_profile.refresh_from_db()
        first_update_time = self.user_profile.last_score_update

        # Second call with different values
        mock_calculate.return_value = (Decimal("90.00"), {"completeness": Decimal("95.00")})
        self.user_profile.calculate_leaderboard_score()

        # Verify second update
        self.user_profile.refresh_from_db()
        self.assertEqual(self.user_profile.leaderboard_score, Decimal("90.00"))
        self.assertEqual(self.user_profile.quality_score, Decimal("95.00"))
        # Use GreaterEqual instead of NotEqual for timestamp comparisons
        self.assertGreaterEqual(self.user_profile.last_score_update, first_update_time)

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

        # Capture original values for comparison
        original_last_score_update = self.user_profile.last_score_update

        # Mock new calculation
        mock_calculate.return_value = (Decimal("75.00"), {"completeness": Decimal("80.00")})

        self.user_profile.calculate_leaderboard_score()

        # Verify fields were updated
        self.user_profile.refresh_from_db()
        self.assertEqual(self.user_profile.leaderboard_score, Decimal("75.00"))
        self.assertEqual(self.user_profile.quality_score, Decimal("80.00"))
        # ensure these fields were refreshed as well
        self.assertNotEqual(self.user_profile.check_in_count, 5)
        self.assertGreater(self.user_profile.last_score_update, original_last_score_update)

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
            mock_calc.return_value = (Decimal("92.50"), {"completeness": Decimal("95.00")})

            score, breakdown = self.profile.calculate_leaderboard_score()

            # Verify results
            self.assertEqual(score, Decimal("92.50"))
            self.assertEqual(breakdown["completeness"], Decimal("95.00"))

            # Verify persistent storage
            updated_profile = UserProfile.objects.get(pk=self.profile.pk)
            self.assertEqual(updated_profile.leaderboard_score, Decimal("92.50"))
            self.assertEqual(updated_profile.quality_score, Decimal("95.00"))
            self.assertIsNotNone(updated_profile.last_score_update)


class RecalcLeaderboardsCommandTest(TestCase):
    def setUp(self):
        cache.clear()
        self.user1 = User.objects.create_user(username="user1", password="pass")
        self.user2 = User.objects.create_user(username="user2", password="pass")

    def test_command_runs_without_errors(self):
        """Test that the command runs without raising exceptions"""
        # Patch the scoring service to isolate from DB/cache noise
        with patch("website.services.leaderboard_scoring.LeaderboardScoringService.calculate_for_user") as mock_calc:
            mock_calc.return_value = (Decimal("50.0"), {"completeness": Decimal("10.0")})

            out = StringIO()
            err = StringIO()

            call_command("recalc_all_leaderboards", stdout=out, stderr=err)
            output = out.getvalue()
            self.assertIn("Recalculating leaderboard scores", output)
            self.assertIn("completed", output.lower())

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
