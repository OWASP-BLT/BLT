from website.models import DailyStatusReport


def test_checkin_triggers_leaderboard_update(self):
    """Test DailyStatusReport creation updates leaderboard score"""
    initial_score = self.profile.leaderboard_score

    DailyStatusReport.objects.create(user=self.user)

    self.profile.refresh_from_db()
    self.assertNotEqual(self.profile.leaderboard_score, initial_score)
