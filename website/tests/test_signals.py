from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from website.models import DailyStatusReport


class DailyStatusReportSignalTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser", email="test@example.com", password="testpass123"
        )
        self.profile = self.user.userprofile

    def test_checkin_triggers_leaderboard_update(self):
        """Test DailyStatusReport creation updates leaderboard score"""
        initial_score = self.profile.leaderboard_score

        DailyStatusReport.objects.create(
            user=self.user,
            date=timezone.now().date(),
            previous_work="prev",
            next_plan="next",
            blockers="none",
        )

        self.profile.refresh_from_db()
        self.assertNotEqual(self.profile.leaderboard_score, initial_score)
