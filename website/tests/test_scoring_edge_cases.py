from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from website.models import DailyStatusReport
from website.services.leaderboard_scoring import LeaderboardScoringService

User = get_user_model()


class LeaderboardScoringEdgeCaseTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="password")

    def test_no_reports(self):
        """Test scoring when user has no reports"""
        score, breakdown = LeaderboardScoringService.calculate_for_user(self.user)
        self.assertEqual(score, 0)
        self.assertEqual(breakdown["frequency"], 0)
        self.assertEqual(breakdown["goals"], 0)

    def test_perfect_frequency(self):
        """Test 100% frequency score"""
        current_time = timezone.now()
        # Create 22 reports (perfect frequency)
        for i in range(22):
            DailyStatusReport.objects.create(
                user=self.user,
                date=current_time.date(),
                created=timezone.now() - timedelta(days=i),
                goal_accomplished=True,
                previous_work="Work",
                next_plan="Plan",
                blockers="None",
                current_mood="Good",
            )

        score, breakdown = LeaderboardScoringService.calculate_for_user(self.user)
        self.assertAlmostEqual(breakdown["frequency"], 100, delta=0.1)

    def test_empty_fields(self):
        """Test reports with missing/empty fields"""
        current_time = timezone.now()
        DailyStatusReport.objects.create(
            user=self.user,
            date=current_time.date(),
            created=current_time,
            goal_accomplished=False,
            previous_work="",
            next_plan="",
            blockers="",
            current_mood="",
        )

        score, breakdown = LeaderboardScoringService.calculate_for_user(self.user)
        self.assertLess(breakdown["completeness"], 100)
