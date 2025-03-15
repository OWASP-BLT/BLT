import datetime

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from website.models import GitHubIssue, Hackathon, Organization, Repo


class HackathonLeaderboardTestCase(TestCase):
    """Test case for the hackathon leaderboard functionality."""

    def setUp(self):
        """Set up test data for the hackathon leaderboard tests."""
        # Create test users
        self.user1 = User.objects.create_user(username="testuser1", email="test1@example.com", password="testpass123")
        self.user2 = User.objects.create_user(username="testuser2", email="test2@example.com", password="testpass123")
        self.user3 = User.objects.create_user(username="testuser3", email="test3@example.com", password="testpass123")

        # Create organization
        self.organization = Organization.objects.create(
            name="Test Organization",
            slug="test-organization",
            url="https://example.com",
        )

        # Create repositories
        self.repo1 = Repo.objects.create(
            name="Test Repo 1",
            slug="test-repo-1",
            repo_url="https://github.com/test/repo1",
            organization=self.organization,
        )
        self.repo2 = Repo.objects.create(
            name="Test Repo 2",
            slug="test-repo-2",
            repo_url="https://github.com/test/repo2",
            organization=self.organization,
        )

        # Create hackathon
        now = timezone.now()
        self.hackathon = Hackathon.objects.create(
            name="Test Hackathon",
            slug="test-hackathon",
            description="A test hackathon for unit testing",
            organization=self.organization,
            start_time=now - datetime.timedelta(days=5),
            end_time=now + datetime.timedelta(days=5),
            is_active=True,
            rules="# Test Rules\n1. Submit PRs\n2. Be awesome",
        )
        self.hackathon.repositories.add(self.repo1, self.repo2)

        # Create pull requests for the hackathon
        # User 1 has 3 PRs (2 in repo1, 1 in repo2)
        for i in range(1, 4):
            repo = self.repo1 if i <= 2 else self.repo2
            GitHubIssue.objects.create(
                issue_id=1000 + i,
                title=f"Test PR {i} by User 1",
                body="Test PR body",
                state="closed",
                type="pull_request",
                created_at=now - datetime.timedelta(days=3),
                updated_at=now - datetime.timedelta(days=2),
                merged_at=now - datetime.timedelta(days=1),
                is_merged=True,
                url=f"https://github.com/test/repo/pull/{1000 + i}",
                repo=repo,
                user_profile=self.user1.userprofile,
            )

        # User 2 has 2 PRs (both in repo2)
        for i in range(1, 3):
            GitHubIssue.objects.create(
                issue_id=2000 + i,
                title=f"Test PR {i} by User 2",
                body="Test PR body",
                state="closed",
                type="pull_request",
                created_at=now - datetime.timedelta(days=3),
                updated_at=now - datetime.timedelta(days=2),
                merged_at=now - datetime.timedelta(days=1),
                is_merged=True,
                url=f"https://github.com/test/repo/pull/{2000 + i}",
                repo=self.repo2,
                user_profile=self.user2.userprofile,
            )

        # User 3 has 1 PR (in repo1)
        GitHubIssue.objects.create(
            issue_id=3001,
            title="Test PR 1 by User 3",
            body="Test PR body",
            state="closed",
            type="pull_request",
            created_at=now - datetime.timedelta(days=3),
            updated_at=now - datetime.timedelta(days=2),
            merged_at=now - datetime.timedelta(days=1),
            is_merged=True,
            url="https://github.com/test/repo/pull/3001",
            repo=self.repo1,
            user_profile=self.user3.userprofile,
        )

        # Create a PR that's outside the hackathon timeframe (should not be counted)
        GitHubIssue.objects.create(
            issue_id=4001,
            title="PR outside timeframe",
            body="This PR is outside the hackathon timeframe",
            state="closed",
            type="pull_request",
            created_at=now - datetime.timedelta(days=10),
            updated_at=now - datetime.timedelta(days=9),
            merged_at=now - datetime.timedelta(days=8),
            is_merged=True,
            url="https://github.com/test/repo/pull/4001",
            repo=self.repo1,
            user_profile=self.user1.userprofile,
        )

        # Create a PR that's not merged (should not be counted)
        GitHubIssue.objects.create(
            issue_id=5001,
            title="Unmerged PR",
            body="This PR is not merged",
            state="open",
            type="pull_request",
            created_at=now - datetime.timedelta(days=3),
            updated_at=now - datetime.timedelta(days=2),
            merged_at=None,
            is_merged=False,
            url="https://github.com/test/repo/pull/5001",
            repo=self.repo1,
            user_profile=self.user1.userprofile,
        )

        self.client = Client()

    def test_hackathon_leaderboard(self):
        """Test that the hackathon leaderboard correctly shows contributors and their PRs."""
        # Get the leaderboard from the model method
        leaderboard = self.hackathon.get_leaderboard()

        # Check the leaderboard order and PR counts
        self.assertEqual(len(leaderboard), 3, "Leaderboard should have 3 contributors")

        # User 1 should be first with 3 PRs
        self.assertEqual(leaderboard[0]["user"].id, self.user1.id)
        self.assertEqual(leaderboard[0]["count"], 3)
        self.assertEqual(len(leaderboard[0]["prs"]), 3)

        # User 2 should be second with 2 PRs
        self.assertEqual(leaderboard[1]["user"].id, self.user2.id)
        self.assertEqual(leaderboard[1]["count"], 2)
        self.assertEqual(len(leaderboard[1]["prs"]), 2)

        # User 3 should be third with 1 PR
        self.assertEqual(leaderboard[2]["user"].id, self.user3.id)
        self.assertEqual(leaderboard[2]["count"], 1)
        self.assertEqual(len(leaderboard[2]["prs"]), 1)

        # Test the hackathon detail view
        response = self.client.get(reverse("hackathon_detail", kwargs={"slug": self.hackathon.slug}))
        self.assertEqual(response.status_code, 200)

        # Check that the leaderboard is in the context
        self.assertIn("leaderboard", response.context)
        view_leaderboard = response.context["leaderboard"]

        # Verify the same data is in the view context
        self.assertEqual(len(view_leaderboard), 3)
        self.assertEqual(view_leaderboard[0]["count"], 3)
        self.assertEqual(view_leaderboard[1]["count"], 2)
        self.assertEqual(view_leaderboard[2]["count"], 1)

        # Check that the template contains the PR titles
        content = response.content.decode("utf-8")
        self.assertIn("Test PR 1 by User 1", content)
        self.assertIn("Test PR 2 by User 1", content)
        self.assertIn("Test PR 3 by User 1", content)
        self.assertIn("Test PR 1 by User 2", content)
        self.assertIn("Test PR 2 by User 2", content)
        self.assertIn("Test PR 1 by User 3", content)

        # Ensure PRs outside the timeframe or unmerged are not included
        self.assertNotIn("PR outside timeframe", content)
        self.assertNotIn("Unmerged PR", content)

    def test_hackathon_leaderboard_empty(self):
        """Test that the hackathon leaderboard handles empty data correctly."""
        # Create a new hackathon with no PRs
        empty_hackathon = Hackathon.objects.create(
            name="Empty Hackathon",
            slug="empty-hackathon",
            description="A hackathon with no PRs",
            organization=self.organization,
            start_time=timezone.now() - datetime.timedelta(days=5),
            end_time=timezone.now() + datetime.timedelta(days=5),
            is_active=True,
        )

        # Create a new repository that has no PRs
        empty_repo = Repo.objects.create(
            name="Empty Repo",
            slug="empty-repo",
            repo_url="https://github.com/test/empty",
            organization=self.organization,
        )

        empty_hackathon.repositories.add(empty_repo)

        # Get the leaderboard
        leaderboard = empty_hackathon.get_leaderboard()

        # Check that the leaderboard is empty
        self.assertEqual(len(leaderboard), 0, "Leaderboard should be empty")

        # Test the hackathon detail view
        response = self.client.get(reverse("hackathon_detail", kwargs={"slug": empty_hackathon.slug}))
        self.assertEqual(response.status_code, 200)

        # Check that the leaderboard is in the context and empty
        self.assertIn("leaderboard", response.context)
        self.assertEqual(len(response.context["leaderboard"]), 0)

        # Check that the template shows the "no contributions" message
        content = response.content.decode("utf-8")
        self.assertIn("No contributions yet", content)

    def test_hackathon_leaderboard_sorting(self):
        """Test that the hackathon leaderboard is sorted correctly by PR count."""
        # Create a new hackathon for sorting test
        now = timezone.now()
        sort_hackathon = Hackathon.objects.create(
            name="Sort Test Hackathon",
            slug="sort-test-hackathon",
            description="A hackathon for testing sorting",
            organization=self.organization,
            start_time=now - datetime.timedelta(days=5),
            end_time=now + datetime.timedelta(days=5),
            is_active=True,
        )

        # Create new repositories for this test to avoid conflicts
        sort_repo1 = Repo.objects.create(
            name="Sort Repo 1",
            slug="sort-repo-1",
            repo_url="https://github.com/test/sort1",
            organization=self.organization,
        )
        sort_repo2 = Repo.objects.create(
            name="Sort Repo 2",
            slug="sort-repo-2",
            repo_url="https://github.com/test/sort2",
            organization=self.organization,
        )

        sort_hackathon.repositories.add(sort_repo1, sort_repo2)

        # Create PRs with different counts to test sorting
        # User 3 has 5 PRs (should be first)
        for i in range(1, 6):
            GitHubIssue.objects.create(
                issue_id=6000 + i,
                title=f"Sort Test PR {i} by User 3",
                body="Test PR body",
                state="closed",
                type="pull_request",
                created_at=now - datetime.timedelta(days=3),
                updated_at=now - datetime.timedelta(days=2),
                merged_at=now - datetime.timedelta(days=1),
                is_merged=True,
                url=f"https://github.com/test/repo/pull/{6000 + i}",
                repo=sort_repo1,
                user_profile=self.user3.userprofile,
            )

        # User 2 has 3 PRs (should be second)
        for i in range(1, 4):
            GitHubIssue.objects.create(
                issue_id=7000 + i,
                title=f"Sort Test PR {i} by User 2",
                body="Test PR body",
                state="closed",
                type="pull_request",
                created_at=now - datetime.timedelta(days=3),
                updated_at=now - datetime.timedelta(days=2),
                merged_at=now - datetime.timedelta(days=1),
                is_merged=True,
                url=f"https://github.com/test/repo/pull/{7000 + i}",
                repo=sort_repo2,
                user_profile=self.user2.userprofile,
            )

        # User 1 has 1 PR (should be third)
        GitHubIssue.objects.create(
            issue_id=8001,
            title="Sort Test PR 1 by User 1",
            body="Test PR body",
            state="closed",
            type="pull_request",
            created_at=now - datetime.timedelta(days=3),
            updated_at=now - datetime.timedelta(days=2),
            merged_at=now - datetime.timedelta(days=1),
            is_merged=True,
            url="https://github.com/test/repo/pull/8001",
            repo=sort_repo1,
            user_profile=self.user1.userprofile,
        )

        # Get the leaderboard
        leaderboard = sort_hackathon.get_leaderboard()

        # Check the leaderboard order and PR counts
        self.assertEqual(len(leaderboard), 3, "Leaderboard should have 3 contributors")

        # User 3 should be first with 5 PRs
        self.assertEqual(leaderboard[0]["user"].id, self.user3.id)
        self.assertEqual(leaderboard[0]["count"], 5)

        # User 2 should be second with 3 PRs
        self.assertEqual(leaderboard[1]["user"].id, self.user2.id)
        self.assertEqual(leaderboard[1]["count"], 3)

        # User 1 should be third with 1 PR
        self.assertEqual(leaderboard[2]["user"].id, self.user1.id)
        self.assertEqual(leaderboard[2]["count"], 1)

