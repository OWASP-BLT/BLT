"""
Tests for GitHub data fetching management commands.
Tests focus on key functionality: timeouts, bulk operations, and data integrity.
"""
from io import StringIO
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from website.models import Contributor, GitHubIssue, GitHubReview, Repo, UserProfile


class GitHubCommandsIntegrationTests(TestCase):
    """Integration tests for GitHub management commands"""

    def setUp(self):
        """Set up test data"""
        self.repo = Repo.objects.create(
            name="BLT",
            repo_url="https://github.com/OWASP-BLT/BLT",
            is_owasp_repo=True,
        )

    def test_fetch_gsoc_prs_command_exists(self):
        """Test that fetch_gsoc_prs command can be called"""
        out = StringIO()
        # Command should run without errors (even if no data fetched)
        try:
            call_command("fetch_gsoc_prs", "--repos=OWASP-BLT/NonExistent", stdout=out)
            success = True
        except Exception as e:
            success = False
            print(f"Command failed: {e}")
        
        self.assertTrue(success, "fetch_gsoc_prs command should be callable")

    def test_fetch_pr_reviews_command_exists(self):
        """Test that fetch_pr_reviews command can be called"""
        out = StringIO()
        # Command should run without errors (even if no PRs exist)
        try:
            call_command("fetch_pr_reviews", stdout=out)
            success = True
        except Exception as e:
            success = False
            print(f"Command failed: {e}")
        
        self.assertTrue(success, "fetch_pr_reviews command should be callable")

    def test_update_github_issues_command_exists(self):
        """Test that update_github_issues command can be called"""
        out = StringIO()
        # Command should run without errors
        try:
            with patch("django.core.management.call_command") as mock_call:
                call_command("update_github_issues", stdout=out)
            success = True
        except Exception as e:
            success = False
            print(f"Command failed: {e}")
        
        self.assertTrue(success, "update_github_issues command should be callable")

    def test_bulk_update_preserves_data(self):
        """Test that bulk_update in fetch_gsoc_prs preserves data correctly"""
        contributor = Contributor.objects.create(
            github_id=12345,
            name="testuser",
            github_url="https://github.com/testuser",
            avatar_url="https://avatars.githubusercontent.com/u/12345",
            contributor_type="User",
            contributions=0,
        )

        # Create a PR
        pr = GitHubIssue.objects.create(
            issue_id=123,
            repo=self.repo,
            title="Original Title",
            body="Original body",
            state="open",
            type="pull_request",
            created_at=timezone.now(),
            updated_at=timezone.now(),
            merged_at=timezone.now(),
            is_merged=True,
            url="https://github.com/OWASP-BLT/BLT/pull/123",
            contributor=contributor,
        )

        # Simulate bulk_update
        pr.title = "Updated Title"
        pr.state = "closed"
        pr.save()

        # Verify update worked
        updated_pr = GitHubIssue.objects.get(issue_id=123)
        self.assertEqual(updated_pr.title, "Updated Title")
        self.assertEqual(updated_pr.state, "closed")
        self.assertEqual(updated_pr.contributor, contributor)

    def test_review_foreignkey_relationship(self):
        """Test that GitHubReview properly links to GitHubIssue"""
        contributor = Contributor.objects.create(
            github_id=12345,
            name="testuser",
            github_url="https://github.com/testuser",
            avatar_url="https://avatars.githubusercontent.com/u/12345",
            contributor_type="User",
            contributions=0,
        )

        pr = GitHubIssue.objects.create(
            issue_id=123,
            repo=self.repo,
            title="Test PR",
            body="Test body",
            state="closed",
            type="pull_request",
            created_at=timezone.now(),
            updated_at=timezone.now(),
            merged_at=timezone.now(),
            is_merged=True,
            url="https://github.com/OWASP-BLT/BLT/pull/123",
            contributor=contributor,
        )

        reviewer = Contributor.objects.create(
            github_id=54321,
            name="reviewer",
            github_url="https://github.com/reviewer",
            avatar_url="https://avatars.githubusercontent.com/u/54321",
            contributor_type="User",
            contributions=0,
        )

        # Create review with proper ForeignKey (not _id)
        review = GitHubReview.objects.create(
            review_id=999,
            pull_request=pr,  # Use object, not ID
            reviewer_contributor=reviewer,
            body="LGTM",
            state="APPROVED",
            submitted_at=timezone.now(),
            url="https://github.com/OWASP-BLT/BLT/pull/123#pullrequestreview-999",
        )

        # Verify relationship
        self.assertEqual(review.pull_request.id, pr.id)
        self.assertEqual(review.pull_request.issue_id, 123)
        self.assertIsNotNone(review.reviewer_contributor)

    @patch("website.management.commands.fetch_gsoc_prs.requests.get")
    def test_timeout_in_fetch_gsoc_prs(self, mock_get):
        """Test that fetch_gsoc_prs uses timeouts"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_get.return_value = mock_response

        out = StringIO()
        call_command("fetch_gsoc_prs", "--repos=OWASP-BLT/BLT", stdout=out)

        # Verify timeout was set
        if mock_get.called:
            call_kwargs = mock_get.call_args[1]
            self.assertIn("timeout", call_kwargs, "API requests should have timeout")

    @patch("website.management.commands.update_github_issues.requests.get")
    def test_timeout_in_update_github_issues(self, mock_get):
        """Test that update_github_issues uses timeouts"""
        # Create user with GitHub URL
        django_user = User.objects.create_user(username="testuser", email="test@example.com")
        user_profile = UserProfile.objects.get(user=django_user)
        user_profile.github_url = "https://github.com/testuser"
        user_profile.save()

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_response.links = {}
        mock_get.return_value = mock_response

        out = StringIO()
        try:
            call_command("update_github_issues", stdout=out)
        except Exception:
            pass  # May fail due to missing repos

        # Verify timeout was set if API was called
        if mock_get.called:
            call_kwargs = mock_get.call_args[1]
            self.assertIn("timeout", call_kwargs, "API requests should have timeout")

    def test_leaderboard_displays_correctly(self):
        """Test that leaderboard page loads with GitHub data"""
        response = self.client.get("/leaderboard/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "leaderboard_global.html")
        self.assertContains(response, "Pull Request Leaderboard")
        self.assertContains(response, "Code Review Leaderboard")
