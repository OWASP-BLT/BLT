"""
Regression tests for award_streak_badges() on UserProfile.

This test file covers the silent ValueError bug caused by using
Badge.objects.get() (returns a single object) instead of
Badge.objects.get_or_create() (returns a (object, created) tuple),
which made tuple-unpacking fail silently, preventing streak badges
from ever being awarded to any user.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from website.models import Badge, UserBadge, UserProfile


class AwardStreakBadgesTest(TestCase):
    """Tests that streak badges are correctly awarded at milestones."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="streakuser",
            email="streak@example.com",
            password="testpass123",
        )

    def test_award_badge_at_7_day_milestone_no_valueerror(self):
        """
        Reaching a 7-day streak must award a badge without raising ValueError.

        Regression test: Badge.objects.get() was incorrectly tuple-unpacked as
        `badge, _ = Badge.objects.get(...)`, which raises ValueError because
        get() returns a single object, not a (instance, created) tuple.
        The exception was silently swallowed, so badges were never awarded.
        """
        profile = self.user.userprofile
        profile.current_streak = 7

        try:
            profile.award_streak_badges()
        except ValueError as exc:
            self.fail(
                f"award_streak_badges() raised ValueError: {exc}. "
                "Ensure Badge.objects.get_or_create() is used, not get()."
            )

        badge = Badge.objects.filter(title="Weekly Streak").first()
        self.assertIsNotNone(badge, "Weekly Streak badge should be created after milestone")
        self.assertTrue(
            UserBadge.objects.filter(user=self.user, badge=badge).exists(),
            "UserBadge record should exist for the user after reaching milestone",
        )

    def test_no_duplicate_badge_on_repeated_calls(self):
        """Calling award_streak_badges twice must not create duplicate UserBadge records."""
        profile = self.user.userprofile
        profile.current_streak = 7

        profile.award_streak_badges()
        profile.award_streak_badges()

        count = UserBadge.objects.filter(
            user=self.user, badge__title="Weekly Streak"
        ).count()
        self.assertEqual(count, 1, "Badge must only be awarded once per milestone")

    def test_no_badge_below_milestone(self):
        """Users below the 7-day threshold must receive no badge."""
        profile = self.user.userprofile
        profile.current_streak = 6  # One below the 7-day milestone

        profile.award_streak_badges()

        self.assertFalse(
            UserBadge.objects.filter(user=self.user).exists(),
            "No badge should be awarded when streak is below any milestone",
        )

    def test_multiple_milestones_award_multiple_badges(self):
        """A streak of 30 should award the 7-day, 15-day, and 30-day badges."""
        profile = self.user.userprofile
        profile.current_streak = 30

        profile.award_streak_badges()

        awarded_titles = set(
            UserBadge.objects.filter(user=self.user).values_list(
                "badge__title", flat=True
            )
        )
        self.assertIn("Weekly Streak", awarded_titles, "7-day badge should be awarded")
        self.assertIn("Half-Month Streak", awarded_titles, "15-day badge should be awarded")
        self.assertIn("Monthly Streak", awarded_titles, "30-day badge should be awarded")
