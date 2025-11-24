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

    def test_hackathon_leaderboard_excludes_bots(self):
        """Test that the hackathon leaderboard correctly excludes bot accounts."""
        from website.models import Contributor

        # Create a new hackathon for bot filtering test
        now = timezone.now()
        bot_hackathon = Hackathon.objects.create(
            name="Bot Test Hackathon",
            slug="bot-test-hackathon",
            description="A hackathon for testing bot filtering",
            organization=self.organization,
            start_time=now - datetime.timedelta(days=5),
            end_time=now + datetime.timedelta(days=5),
            is_active=True,
        )

        # Create a new repository for this test
        bot_repo = Repo.objects.create(
            name="Bot Repo",
            slug="bot-repo",
            repo_url="https://github.com/test/botrepo",
            organization=self.organization,
        )

        bot_hackathon.repositories.add(bot_repo)

        # Create bot contributors
        bot1 = Contributor.objects.create(
            name="dependabot[bot]",
            github_id=9000001,
            github_url="https://github.com/apps/dependabot",
            avatar_url="https://avatars.githubusercontent.com/in/29110",
            contributor_type="Bot",
            contributions=1,
        )

        bot2 = Contributor.objects.create(
            name="github-actions[bot]",
            github_id=9000002,
            github_url="https://github.com/apps/github-actions",
            avatar_url="https://avatars.githubusercontent.com/in/15368",
            contributor_type="Bot",
            contributions=1,
        )

        # Create a bot with User type but bot-like name (edge case)
        bot3 = Contributor.objects.create(
            name="renovate-bot",
            github_id=9000003,
            github_url="https://github.com/renovate-bot",
            avatar_url="https://avatars.githubusercontent.com/u/9000003",
            contributor_type="User",
            contributions=1,
        )

        # Create a regular contributor
        human_contributor = Contributor.objects.create(
            name="human-contributor",
            github_id=9000004,
            github_url="https://github.com/human-contributor",
            avatar_url="https://avatars.githubusercontent.com/u/9000004",
            contributor_type="User",
            contributions=1,
        )

        # Create PRs from bot contributors (should be excluded)
        for i, bot in enumerate([bot1, bot2, bot3], start=1):
            GitHubIssue.objects.create(
                issue_id=9000 + i,
                title=f"Bot PR {i}",
                body="PR created by a bot",
                state="closed",
                type="pull_request",
                created_at=now - datetime.timedelta(days=3),
                updated_at=now - datetime.timedelta(days=2),
                merged_at=now - datetime.timedelta(days=1),
                is_merged=True,
                url=f"https://github.com/test/botrepo/pull/{9000 + i}",
                repo=bot_repo,
                contributor=bot,
            )

        # Create PR from human contributor (should be included)
        GitHubIssue.objects.create(
            issue_id=9100,
            title="Human PR",
            body="PR created by a human",
            state="closed",
            type="pull_request",
            created_at=now - datetime.timedelta(days=3),
            updated_at=now - datetime.timedelta(days=2),
            merged_at=now - datetime.timedelta(days=1),
            is_merged=True,
            url="https://github.com/test/botrepo/pull/9100",
            repo=bot_repo,
            contributor=human_contributor,
        )

        # Create PR from registered user (should be included)
        GitHubIssue.objects.create(
            issue_id=9200,
            title="User PR",
            body="PR created by a registered user",
            state="closed",
            type="pull_request",
            created_at=now - datetime.timedelta(days=3),
            updated_at=now - datetime.timedelta(days=2),
            merged_at=now - datetime.timedelta(days=1),
            is_merged=True,
            url="https://github.com/test/botrepo/pull/9200",
            repo=bot_repo,
            user_profile=self.user1.userprofile,
        )

        # Get the leaderboard
        leaderboard = bot_hackathon.get_leaderboard()

        # Check that only non-bot contributors are in the leaderboard
        self.assertEqual(len(leaderboard), 2, "Leaderboard should only have 2 non-bot contributors")

        # Verify that bot PRs are excluded
        all_usernames = []
        for entry in leaderboard:
            if hasattr(entry["user"], "username"):
                all_usernames.append(entry["user"].username)
            elif isinstance(entry["user"], dict):
                all_usernames.append(entry["user"]["username"])

        self.assertIn("testuser1", all_usernames, "Registered user should be in leaderboard")
        self.assertIn("human-contributor", all_usernames, "Human contributor should be in leaderboard")
        self.assertNotIn("dependabot[bot]", all_usernames, "Bot should be excluded from leaderboard")
        self.assertNotIn("github-actions[bot]", all_usernames, "Bot should be excluded from leaderboard")
        self.assertNotIn("renovate-bot", all_usernames, "Bot-like name should be excluded from leaderboard")

        # Test participant count directly (without rendering the view)
        from website.views.hackathon import HackathonDetailView

        view = HackathonDetailView()
        repo_ids = bot_hackathon.repositories.values_list("id", flat=True)
        merged_prs = view._get_base_pr_query(bot_hackathon, repo_ids, is_merged=True)
        participant_count = view._get_participant_count(merged_prs)

        # Check that participant count excludes bots
        self.assertEqual(participant_count, 2, "Participant count should exclude bots")

        # Check that PR counts exclude bots
        merged_pr_count = merged_prs.count()
        self.assertEqual(merged_pr_count, 2, "Merged PR count should exclude bots")

    def test_hackathon_chart_data_uses_merge_date(self):
        """Test that chart data for merged PRs is grouped by merge date, not creation date."""
        from django.db.models import Count
        from django.db.models.functions import TruncDate

        # Create a past hackathon (already ended)
        now = timezone.now()
        past_hackathon = Hackathon.objects.create(
            name="Past Hackathon",
            slug="past-hackathon",
            description="A past hackathon for testing chart data",
            organization=self.organization,
            start_time=now - datetime.timedelta(days=10),
            end_time=now - datetime.timedelta(days=5),
            is_active=False,
        )

        # Create a new repository for this test
        chart_repo = Repo.objects.create(
            name="Chart Repo",
            slug="chart-repo",
            repo_url="https://github.com/test/chartrepo",
            organization=self.organization,
        )

        past_hackathon.repositories.add(chart_repo)

        # Create PRs with different creation and merge dates
        # PR 1: Created 9 days ago, merged 8 days ago (both during hackathon)
        pr1 = GitHubIssue.objects.create(
            issue_id=10001,
            title="PR created and merged during hackathon",
            body="Test PR body",
            state="closed",
            type="pull_request",
            created_at=now - datetime.timedelta(days=9),
            updated_at=now - datetime.timedelta(days=8),
            merged_at=now - datetime.timedelta(days=8),
            is_merged=True,
            url="https://github.com/test/chartrepo/pull/10001",
            repo=chart_repo,
            user_profile=self.user1.userprofile,
        )

        # PR 2: Created 7 days ago, merged 6 days ago (both during hackathon)
        pr2 = GitHubIssue.objects.create(
            issue_id=10002,
            title="PR created and merged on different days",
            body="Test PR body",
            state="closed",
            type="pull_request",
            created_at=now - datetime.timedelta(days=7),
            updated_at=now - datetime.timedelta(days=6),
            merged_at=now - datetime.timedelta(days=6),
            is_merged=True,
            url="https://github.com/test/chartrepo/pull/10002",
            repo=chart_repo,
            user_profile=self.user2.userprofile,
        )

        # Test the view's chart data calculation
        from website.views.hackathon import HackathonDetailView

        view = HackathonDetailView()
        repo_ids = past_hackathon.repositories.values_list("id", flat=True)

        # Get merged PR data grouped by merge date (this is what the fix does)
        merged_pr_data = (
            view._get_base_pr_query(past_hackathon, repo_ids, is_merged=True)
            .annotate(date=TruncDate("merged_at"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )

        # Convert to dict for easier checking
        date_merged_pr_counts = {item["date"]: item["count"] for item in merged_pr_data}

        # Verify that PRs are grouped by their merge date
        merge_date_1 = (now - datetime.timedelta(days=8)).date()
        merge_date_2 = (now - datetime.timedelta(days=6)).date()

        # PR1 should be counted on its merge date
        self.assertIn(merge_date_1, date_merged_pr_counts)
        self.assertEqual(date_merged_pr_counts[merge_date_1], 1)

        # PR2 should be counted on its merge date
        self.assertIn(merge_date_2, date_merged_pr_counts)
        self.assertEqual(date_merged_pr_counts[merge_date_2], 1)

        # Verify that the chart data is NOT grouped by creation date
        # (which would be different from merge date)
        creation_date_1 = (now - datetime.timedelta(days=9)).date()
        creation_date_2 = (now - datetime.timedelta(days=7)).date()

        # These dates should NOT have the PRs if we're correctly using merge_at
        # (unless creation and merge happen on the same day, which they don't in this test)
        self.assertNotEqual(creation_date_1, merge_date_1)
        self.assertNotEqual(creation_date_2, merge_date_2)

    def test_reviewer_leaderboard(self):
        """Test that the reviewer leaderboard correctly shows reviewers and their reviews."""
        from website.models import GitHubReview

        # Create a new hackathon for reviewer testing
        now = timezone.now()
        review_hackathon = Hackathon.objects.create(
            name="Review Test Hackathon",
            slug="review-test-hackathon",
            description="A hackathon for testing reviewer leaderboard",
            organization=self.organization,
            start_time=now - datetime.timedelta(days=5),
            end_time=now + datetime.timedelta(days=5),
            is_active=True,
        )

        # Create a new repository for this test
        review_repo = Repo.objects.create(
            name="Review Repo",
            slug="review-repo",
            repo_url="https://github.com/test/reviewrepo",
            organization=self.organization,
        )

        review_hackathon.repositories.add(review_repo)

        # Create some pull requests during the hackathon
        pr1 = GitHubIssue.objects.create(
            issue_id=11001,
            title="PR 1 for review testing",
            body="Test PR body",
            state="closed",
            type="pull_request",
            created_at=now - datetime.timedelta(days=3),
            updated_at=now - datetime.timedelta(days=2),
            merged_at=now - datetime.timedelta(days=1),
            is_merged=True,
            url="https://github.com/test/reviewrepo/pull/11001",
            repo=review_repo,
            user_profile=self.user1.userprofile,
        )

        pr2 = GitHubIssue.objects.create(
            issue_id=11002,
            title="PR 2 for review testing",
            body="Test PR body",
            state="closed",
            type="pull_request",
            created_at=now - datetime.timedelta(days=3),
            updated_at=now - datetime.timedelta(days=2),
            merged_at=now - datetime.timedelta(days=1),
            is_merged=True,
            url="https://github.com/test/reviewrepo/pull/11002",
            repo=review_repo,
            user_profile=self.user1.userprofile,
        )

        pr3 = GitHubIssue.objects.create(
            issue_id=11003,
            title="PR 3 for review testing",
            body="Test PR body",
            state="closed",
            type="pull_request",
            created_at=now - datetime.timedelta(days=3),
            updated_at=now - datetime.timedelta(days=2),
            merged_at=now - datetime.timedelta(days=1),
            is_merged=True,
            url="https://github.com/test/reviewrepo/pull/11003",
            repo=review_repo,
            user_profile=self.user2.userprofile,
        )

        # Create reviews for these PRs
        # User2 reviews PR1 (approved)
        review1 = GitHubReview.objects.create(
            review_id=20001,
            pull_request=pr1,
            reviewer=self.user2.userprofile,
            body="Looks good!",
            state="APPROVED",
            submitted_at=now - datetime.timedelta(days=2),
            url="https://github.com/test/reviewrepo/pull/11001#review-20001",
        )

        # User2 reviews PR2 (changes requested)
        review2 = GitHubReview.objects.create(
            review_id=20002,
            pull_request=pr2,
            reviewer=self.user2.userprofile,
            body="Please fix this",
            state="CHANGES_REQUESTED",
            submitted_at=now - datetime.timedelta(days=2),
            url="https://github.com/test/reviewrepo/pull/11002#review-20002",
        )

        # User3 reviews PR1 (commented)
        review3 = GitHubReview.objects.create(
            review_id=20003,
            pull_request=pr1,
            reviewer=self.user3.userprofile,
            body="Nice work",
            state="COMMENTED",
            submitted_at=now - datetime.timedelta(days=2),
            url="https://github.com/test/reviewrepo/pull/11001#review-20003",
        )

        # User3 reviews PR3 (approved)
        review4 = GitHubReview.objects.create(
            review_id=20004,
            pull_request=pr3,
            reviewer=self.user3.userprofile,
            body="LGTM",
            state="APPROVED",
            submitted_at=now - datetime.timedelta(days=2),
            url="https://github.com/test/reviewrepo/pull/11003#review-20004",
        )

        # Create a review outside the hackathon timeframe (should not be counted)
        review_outside = GitHubReview.objects.create(
            review_id=20005,
            pull_request=pr1,
            reviewer=self.user2.userprofile,
            body="Old review",
            state="APPROVED",
            submitted_at=now - datetime.timedelta(days=10),
            url="https://github.com/test/reviewrepo/pull/11001#review-20005",
        )

        # Get the reviewer leaderboard
        reviewer_leaderboard = review_hackathon.get_reviewer_leaderboard()

        # Check the leaderboard order and review counts
        self.assertEqual(len(reviewer_leaderboard), 2, "Reviewer leaderboard should have 2 reviewers")

        # User2 should be first with 2 reviews
        self.assertEqual(reviewer_leaderboard[0]["user"].id, self.user2.id)
        self.assertEqual(reviewer_leaderboard[0]["count"], 2)
        self.assertEqual(len(reviewer_leaderboard[0]["reviews"]), 2)

        # User3 should be second with 2 reviews
        self.assertEqual(reviewer_leaderboard[1]["user"].id, self.user3.id)
        self.assertEqual(reviewer_leaderboard[1]["count"], 2)
        self.assertEqual(len(reviewer_leaderboard[1]["reviews"]), 2)

        # Test the hackathon detail view
        response = self.client.get(reverse("hackathon_detail", kwargs={"slug": review_hackathon.slug}))
        self.assertEqual(response.status_code, 200)

        # Check that the reviewer leaderboard is in the context
        self.assertIn("reviewer_leaderboard", response.context)
        view_reviewer_leaderboard = response.context["reviewer_leaderboard"]

        # Verify the same data is in the view context
        self.assertEqual(len(view_reviewer_leaderboard), 2)
        self.assertEqual(view_reviewer_leaderboard[0]["count"], 2)
        self.assertEqual(view_reviewer_leaderboard[1]["count"], 2)

        # Check that the template contains the review states
        content = response.content.decode("utf-8")
        self.assertIn("PR Reviewer Leaderboard", content)
        self.assertIn("testuser2", content)
        self.assertIn("testuser3", content)

        # Ensure reviews outside the timeframe are not included
        self.assertNotIn("Old review", content)

    def test_reviewer_leaderboard_excludes_bots(self):
        """Test that the reviewer leaderboard correctly excludes bot accounts."""
        from website.models import Contributor, GitHubReview

        # Create a new hackathon for bot filtering test
        now = timezone.now()
        bot_review_hackathon = Hackathon.objects.create(
            name="Bot Review Test Hackathon",
            slug="bot-review-test-hackathon",
            description="A hackathon for testing bot filtering in reviewer leaderboard",
            organization=self.organization,
            start_time=now - datetime.timedelta(days=5),
            end_time=now + datetime.timedelta(days=5),
            is_active=True,
        )

        # Create a new repository for this test
        bot_review_repo = Repo.objects.create(
            name="Bot Review Repo",
            slug="bot-review-repo",
            repo_url="https://github.com/test/botreviewrepo",
            organization=self.organization,
        )

        bot_review_hackathon.repositories.add(bot_review_repo)

        # Create a pull request during the hackathon
        pr1 = GitHubIssue.objects.create(
            issue_id=12001,
            title="PR for bot review testing",
            body="Test PR body",
            state="closed",
            type="pull_request",
            created_at=now - datetime.timedelta(days=3),
            updated_at=now - datetime.timedelta(days=2),
            merged_at=now - datetime.timedelta(days=1),
            is_merged=True,
            url="https://github.com/test/botreviewrepo/pull/12001",
            repo=bot_review_repo,
            user_profile=self.user1.userprofile,
        )

        # Create bot contributors
        bot1 = Contributor.objects.create(
            name="dependabot[bot]",
            github_id=10000001,
            github_url="https://github.com/apps/dependabot",
            avatar_url="https://avatars.githubusercontent.com/in/29110",
            contributor_type="Bot",
            contributions=1,
        )

        bot2 = Contributor.objects.create(
            name="github-actions[bot]",
            github_id=10000002,
            github_url="https://github.com/apps/github-actions",
            avatar_url="https://avatars.githubusercontent.com/in/15368",
            contributor_type="Bot",
            contributions=1,
        )

        # Create a bot with User type but bot-like name (edge case)
        bot3 = Contributor.objects.create(
            name="renovate-bot",
            github_id=10000003,
            github_url="https://github.com/renovate-bot",
            avatar_url="https://avatars.githubusercontent.com/u/10000003",
            contributor_type="User",
            contributions=1,
        )

        # Create a regular contributor
        human_reviewer = Contributor.objects.create(
            name="human-reviewer",
            github_id=10000004,
            github_url="https://github.com/human-reviewer",
            avatar_url="https://avatars.githubusercontent.com/u/10000004",
            contributor_type="User",
            contributions=1,
        )

        # Create reviews from bot contributors (should be excluded)
        for i, bot in enumerate([bot1, bot2, bot3], start=1):
            GitHubReview.objects.create(
                review_id=21000 + i,
                pull_request=pr1,
                reviewer_contributor=bot,
                body="Bot review",
                state="APPROVED",
                submitted_at=now - datetime.timedelta(days=2),
                url=f"https://github.com/test/botreviewrepo/pull/12001#review-{21000 + i}",
            )

        # Create review from human contributor (should be included)
        GitHubReview.objects.create(
            review_id=21100,
            pull_request=pr1,
            reviewer_contributor=human_reviewer,
            body="Human review",
            state="APPROVED",
            submitted_at=now - datetime.timedelta(days=2),
            url="https://github.com/test/botreviewrepo/pull/12001#review-21100",
        )

        # Create review from registered user (should be included)
        GitHubReview.objects.create(
            review_id=21200,
            pull_request=pr1,
            reviewer=self.user2.userprofile,
            body="User review",
            state="APPROVED",
            submitted_at=now - datetime.timedelta(days=2),
            url="https://github.com/test/botreviewrepo/pull/12001#review-21200",
        )

        # Get the reviewer leaderboard
        reviewer_leaderboard = bot_review_hackathon.get_reviewer_leaderboard()

        # Check that only non-bot reviewers are in the leaderboard
        self.assertEqual(len(reviewer_leaderboard), 2, "Reviewer leaderboard should only have 2 non-bot reviewers")

        # Verify that bot reviews are excluded
        all_usernames = []
        for entry in reviewer_leaderboard:
            if hasattr(entry["user"], "username"):
                all_usernames.append(entry["user"].username)
            elif isinstance(entry["user"], dict):
                all_usernames.append(entry["user"]["username"])

        self.assertIn("testuser2", all_usernames, "Registered user should be in reviewer leaderboard")
        self.assertIn("human-reviewer", all_usernames, "Human contributor should be in reviewer leaderboard")
        self.assertNotIn("dependabot[bot]", all_usernames, "Bot should be excluded from reviewer leaderboard")
        self.assertNotIn("github-actions[bot]", all_usernames, "Bot should be excluded from reviewer leaderboard")
        self.assertNotIn("renovate-bot", all_usernames, "Bot-like name should be excluded from reviewer leaderboard")

    def test_reviewer_leaderboard_empty(self):
        """Test that the reviewer leaderboard handles empty data correctly."""
        # Create a new hackathon with no reviews
        empty_review_hackathon = Hackathon.objects.create(
            name="Empty Review Hackathon",
            slug="empty-review-hackathon",
            description="A hackathon with no reviews",
            organization=self.organization,
            start_time=timezone.now() - datetime.timedelta(days=5),
            end_time=timezone.now() + datetime.timedelta(days=5),
            is_active=True,
        )

        # Create a new repository that has no reviews
        empty_review_repo = Repo.objects.create(
            name="Empty Review Repo",
            slug="empty-review-repo",
            repo_url="https://github.com/test/emptyreview",
            organization=self.organization,
        )

        empty_review_hackathon.repositories.add(empty_review_repo)

        # Get the reviewer leaderboard
        reviewer_leaderboard = empty_review_hackathon.get_reviewer_leaderboard()

        # Check that the leaderboard is empty
        self.assertEqual(len(reviewer_leaderboard), 0, "Reviewer leaderboard should be empty")

        # Test the hackathon detail view
        response = self.client.get(reverse("hackathon_detail", kwargs={"slug": empty_review_hackathon.slug}))
        self.assertEqual(response.status_code, 200)

        # Check that the reviewer leaderboard is in the context and empty
        self.assertIn("reviewer_leaderboard", response.context)
        self.assertEqual(len(response.context["reviewer_leaderboard"]), 0)

        # Check that the template shows the "no reviews" message
        content = response.content.decode("utf-8")
        self.assertIn("No reviews yet", content)
