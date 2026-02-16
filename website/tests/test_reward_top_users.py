from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from website.models import BaconEarning, Points, UserProfile


class RewardTopUsersCommandTest(TestCase):
    def setUp(self):
        """Create test users with points for the previous month."""
        self.users = []
        for i in range(5):
            user = User.objects.create_user(
                username=f"testuser{i}",
                email=f"test{i}@example.com",
                password="testpass123",
            )
            UserProfile.objects.get_or_create(user=user)
            self.users.append(user)

        # Award different points to each user in the previous month
        now = timezone.now()
        first_of_current = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        prev_month = first_of_current - timedelta(days=1)
        point_values = [100, 80, 60, 40, 20]
        for user, points in zip(self.users, point_values):
            Points.objects.create(user=user, score=points, created=prev_month)

    def test_dry_run_does_not_award_bacon(self):
        """Dry run should show rewards but not actually give BACON."""
        out = StringIO()
        call_command("reward_top_users", "--dry-run", stdout=out)
        output = out.getvalue()

        self.assertIn("DRY RUN", output)
        # Verify no BaconEarning was created/updated
        for user in self.users:
            earnings = BaconEarning.objects.filter(user=user)
            if earnings.exists():
                self.assertEqual(earnings.first().tokens_earned, 0)

    @patch("website.management.commands.reward_top_users.giveBacon")
    def test_rewards_top_users(self, mock_give_bacon):
        """Should award BACON to top users based on their rank."""
        mock_give_bacon.return_value = 50
        out = StringIO()
        call_command("reward_top_users", "--top", "3", stdout=out)
        output = out.getvalue()

        # Should have called giveBacon 3 times (top 3 users)
        self.assertEqual(mock_give_bacon.call_count, 3)

        # First place user should get 50 BACON
        first_call = mock_give_bacon.call_args_list[0]
        self.assertEqual(first_call[0][0], self.users[0])
        self.assertEqual(first_call[1]["amt"], 50)

        # Second place user should get 40 BACON
        second_call = mock_give_bacon.call_args_list[1]
        self.assertEqual(second_call[0][0], self.users[1])
        self.assertEqual(second_call[1]["amt"], 40)

        # Third place user should get 30 BACON
        third_call = mock_give_bacon.call_args_list[2]
        self.assertEqual(third_call[0][0], self.users[2])
        self.assertEqual(third_call[1]["amt"], 30)

    @patch("website.management.commands.reward_top_users.giveBacon")
    def test_rewards_correct_tier_amounts(self, mock_give_bacon):
        """Verify reward tiers: 1st=50, 2nd=40, 3rd=30, 4th-5th=20."""
        mock_give_bacon.return_value = 1
        out = StringIO()
        call_command("reward_top_users", "--top", "5", stdout=out)

        expected_amounts = [50, 40, 30, 20, 20]
        for i, expected_amt in enumerate(expected_amounts):
            actual_amt = mock_give_bacon.call_args_list[i][1]["amt"]
            self.assertEqual(actual_amt, expected_amt, f"Rank {i + 1} should get {expected_amt} BACON")

    def test_no_users_with_points(self):
        """Should handle case where no users have points in the period."""
        Points.objects.all().delete()
        out = StringIO()
        call_command("reward_top_users", stdout=out)
        output = out.getvalue()

        self.assertIn("No users found", output)

    @patch("website.management.commands.reward_top_users.giveBacon")
    def test_weekly_period(self, mock_give_bacon):
        """Should support weekly period option."""
        mock_give_bacon.return_value = 50
        # Create points within the last week for the weekly test
        recent = timezone.now() - timedelta(days=2)
        Points.objects.create(user=self.users[0], score=200, created=recent)
        out = StringIO()
        call_command("reward_top_users", "--period", "week", "--top", "1", stdout=out)
        output = out.getvalue()

        self.assertIn("week of", output)
        self.assertEqual(mock_give_bacon.call_count, 1)
