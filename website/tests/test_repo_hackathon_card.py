import datetime

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from website.models import Contributor, GitHubIssue, Hackathon, Organization, Repo


class RepoHackathonCardTestCase(TestCase):
    """Test case for the active hackathon card on repo detail page."""

    def setUp(self):
        """Set up test data for the repo hackathon card tests."""
        # Create test user
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")

        # Create organization
        self.organization = Organization.objects.create(
            name="Test Organization",
            slug="test-organization",
            url="https://example.com",
        )

        # Create repository
        self.repo = Repo.objects.create(
            name="Test Repo",
            slug="test-repo",
            repo_url="https://github.com/test/repo",
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
        )

        # Link repository to hackathon
        self.hackathon.repositories.add(self.repo)

        # Create a contributor
        self.contributor = Contributor.objects.create(
            name="TestContributor",
            github_id=12345,
            github_url="https://github.com/testcontributor",
            avatar_url="https://avatars.githubusercontent.com/u/12345?v=4",
            contributor_type="User",
        )

        # Create some test pull requests
        for i in range(3):
            GitHubIssue.objects.create(
                issue_id=i + 1,
                title=f"Test PR {i + 1}",
                body="Test PR body",
                state="closed" if i < 2 else "open",
                type="pull_request",
                created_at=now - datetime.timedelta(days=3),
                updated_at=now - datetime.timedelta(days=2),
                merged_at=now - datetime.timedelta(days=1) if i < 2 else None,
                is_merged=i < 2,
                url=f"https://github.com/test/repo/pull/{i + 1}",
                repo=self.repo,
                contributor=self.contributor,
            )

        self.client = Client()

    def test_repo_detail_shows_active_hackathon_card(self):
        """Test that repo detail page shows active hackathon card."""
        response = self.client.get(reverse("repo_detail", kwargs={"slug": self.repo.slug}))

        self.assertEqual(response.status_code, 200)
        self.assertIn("active_hackathon", response.context)
        self.assertIsNotNone(response.context["active_hackathon"])
        self.assertEqual(response.context["active_hackathon"].slug, self.hackathon.slug)

    def test_active_hackathon_stats_are_calculated(self):
        """Test that hackathon stats are correctly calculated."""
        response = self.client.get(reverse("repo_detail", kwargs={"slug": self.repo.slug}))

        self.assertEqual(response.status_code, 200)
        self.assertIn("active_hackathon_stats", response.context)

        stats = response.context["active_hackathon_stats"]
        self.assertIn("total_prs", stats)
        self.assertIn("merged_prs", stats)
        self.assertIn("participants", stats)

        # Verify the stats
        self.assertEqual(stats["total_prs"], 3)  # All 3 PRs
        self.assertEqual(stats["merged_prs"], 2)  # 2 merged PRs
        self.assertEqual(stats["participants"], 1)  # 1 contributor

    def test_no_active_hackathon_card_when_none_exists(self):
        """Test that no hackathon card is shown when there's no active hackathon."""
        # Make the hackathon inactive
        self.hackathon.is_active = False
        self.hackathon.save()

        response = self.client.get(reverse("repo_detail", kwargs={"slug": self.repo.slug}))

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("active_hackathon", response.context)

    def test_no_active_hackathon_card_when_hackathon_ended(self):
        """Test that no hackathon card is shown when the hackathon has ended."""
        # Make the hackathon end in the past
        now = timezone.now()
        self.hackathon.start_time = now - datetime.timedelta(days=10)
        self.hackathon.end_time = now - datetime.timedelta(days=1)
        self.hackathon.save()

        response = self.client.get(reverse("repo_detail", kwargs={"slug": self.repo.slug}))

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("active_hackathon", response.context)

    def test_active_hackathon_card_html_rendered(self):
        """Test that the hackathon card HTML is rendered on the page."""
        response = self.client.get(reverse("repo_detail", kwargs={"slug": self.repo.slug}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Active Hackathon")
        self.assertContains(response, self.hackathon.name)
        self.assertContains(response, "View Hackathon Details")

    def test_bot_contributors_excluded_from_stats(self):
        """Test that bot contributors are excluded from participant count."""
        # Create a bot contributor
        bot_contributor = Contributor.objects.create(
            name="github-bot[bot]",
            github_id=54321,
            github_url="https://github.com/apps/github-bot",
            avatar_url="https://avatars.githubusercontent.com/u/54321?v=4",
            contributor_type="Bot",
        )

        # Create a PR by the bot
        now = timezone.now()
        GitHubIssue.objects.create(
            issue_id=100,
            title="Bot PR",
            body="Automated PR",
            state="closed",
            type="pull_request",
            created_at=now - datetime.timedelta(days=3),
            updated_at=now - datetime.timedelta(days=2),
            merged_at=now - datetime.timedelta(days=1),
            is_merged=True,
            url="https://github.com/test/repo/pull/100",
            repo=self.repo,
            contributor=bot_contributor,
        )

        response = self.client.get(reverse("repo_detail", kwargs={"slug": self.repo.slug}))

        self.assertEqual(response.status_code, 200)
        stats = response.context["active_hackathon_stats"]

        # Bot PRs are excluded from both total_prs count and participant count
        self.assertEqual(stats["total_prs"], 3)  # Only the 3 non-bot PRs from setUp
        self.assertEqual(stats["participants"], 1)  # Bot not counted as participant
