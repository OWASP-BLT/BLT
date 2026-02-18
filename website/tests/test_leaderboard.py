from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from website.management.commands.leaderboard import get_title_for_count
from website.models import Issue, UserProfile


class LeaderboardCommandTest(TestCase):
    def setUp(self):
        """Create test users with different issue counts."""
        self.users = []
        for i in range(4):
            user = User.objects.create_user(
                username=f"leaderuser{i}",
                email=f"leader{i}@example.com",
                password="testpass123",
            )
            UserProfile.objects.get_or_create(user=user)
            self.users.append(user)

    def _create_issues(self, user, count):
        """Helper to create a given number of issues for a user."""
        for _ in range(count):
            Issue.objects.create(
                user=user,
                url=f"https://example.com/{user.username}",
            )

    def test_title_thresholds(self):
        """Test that get_title_for_count returns correct title levels."""
        self.assertEqual(get_title_for_count(0), 1)
        self.assertEqual(get_title_for_count(10), 1)
        self.assertEqual(get_title_for_count(11), 2)
        self.assertEqual(get_title_for_count(50), 2)
        self.assertEqual(get_title_for_count(51), 3)
        self.assertEqual(get_title_for_count(200), 3)
        self.assertEqual(get_title_for_count(201), 4)
        self.assertEqual(get_title_for_count(1000), 4)

    def test_updates_user_titles(self):
        """Command should update titles based on issue count."""
        # Give users different issue counts spanning all tiers
        self._create_issues(self.users[0], 5)  # <= 10 -> title 1
        self._create_issues(self.users[1], 30)  # <= 50 -> title 2
        self._create_issues(self.users[2], 100)  # <= 200 -> title 3
        self._create_issues(self.users[3], 250)  # > 200 -> title 4

        out = StringIO()
        call_command("leaderboard", stdout=out)

        # Refresh from DB
        for user in self.users:
            user.userprofile.refresh_from_db()

        self.assertEqual(self.users[0].userprofile.title, 1)
        self.assertEqual(self.users[1].userprofile.title, 2)
        self.assertEqual(self.users[2].userprofile.title, 3)
        self.assertEqual(self.users[3].userprofile.title, 4)

    def test_no_issues_gives_title_1(self):
        """Users with no issues should get title 1."""
        out = StringIO()
        call_command("leaderboard", stdout=out)

        for user in self.users:
            user.userprofile.refresh_from_db()
            self.assertEqual(user.userprofile.title, 1)

    def test_only_updates_changed_profiles(self):
        """Command should report how many profiles were actually updated."""
        # Set all profiles to title 1 (which matches 0 issues)
        for user in self.users:
            profile = user.userprofile
            profile.title = 1
            profile.save()

        out = StringIO()
        call_command("leaderboard", stdout=out)
        output = out.getvalue()

        # No issues, all already title 1, so 0 should be updated
        self.assertIn("Updated 0", output)

    def test_output_format(self):
        """Command should output update count."""
        out = StringIO()
        call_command("leaderboard", stdout=out)
        output = out.getvalue()

        self.assertIn("Updated", output)
        self.assertIn("user titles", output)
