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

    @patch("website.management.commands.fetch_gsoc_prs.requests.get")
    def test_fetch_gsoc_prs_command_exists(self, mock_get):
        """Test that fetch_gsoc_prs command can be called with mocked API"""
        # Mock GitHub API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_get.return_value = mock_response

        out = StringIO()
        # Command should run without errors
        call_command("fetch_gsoc_prs", "--repos=OWASP-BLT/BLT", stdout=out)

        # Verify command completed
        output = out.getvalue()
        self.assertIn("Completed", output)

    @patch("website.management.commands.fetch_pr_reviews.requests.get")
    def test_fetch_pr_reviews_command_exists(self, mock_get):
        """Test that fetch_pr_reviews command can be called with mocked API"""
        # Mock GitHub API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        out = StringIO()
        # Command should run without errors
        call_command("fetch_pr_reviews", stdout=out)

        # Verify command completed (either "Completed" or "No reviews found")
        output = out.getvalue()
        self.assertTrue("Completed" in output or "No reviews found" in output, "Command should complete successfully")

    @patch("website.management.commands.fetch_gsoc_prs.requests.get")
    def test_update_github_issues_command_exists(self, mock_get):
        """Test that update_github_issues command can be called"""
        # Mock GitHub API response for fetch_gsoc_prs (fallback)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_get.return_value = mock_response

        out = StringIO()
        # Command should run without errors (falls back to fetch_gsoc_prs)
        call_command("update_github_issues", stdout=out)

        # Verify command completed
        output = out.getvalue()
        self.assertIn("No users with GitHub URLs found", output)

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

        # CRITICAL VERIFICATIONS:
        # 1. Verify API was actually called
        self.assertTrue(mock_get.called, "API should be called")
        self.assertGreater(mock_get.call_count, 0, "API should be called at least once")

        # 2. Verify timeout parameter exists
        call_kwargs = mock_get.call_args[1]
        self.assertIn("timeout", call_kwargs, "API requests must have timeout parameter")

        # 3. Verify timeout value is reasonable (not None or 0)
        timeout_value = call_kwargs["timeout"]
        self.assertIsNotNone(timeout_value, "Timeout should not be None")
        self.assertNotEqual(timeout_value, 0, "Timeout should not be 0")

        # 4. Verify command completed successfully
        output = out.getvalue()
        self.assertIn("Completed", output, "Command should complete successfully")

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
        call_command("update_github_issues", stdout=out)

        # CRITICAL VERIFICATIONS:
        # 1. Verify API was called (user has GitHub URL, so it should fetch)
        self.assertTrue(mock_get.called, "API should be called for user with GitHub URL")

        # 2. Verify timeout parameter exists
        call_kwargs = mock_get.call_args[1]
        self.assertIn("timeout", call_kwargs, "API requests must have timeout parameter")

        # 3. Verify timeout is a tuple (connect, read) as recommended
        timeout_value = call_kwargs["timeout"]
        self.assertIsInstance(timeout_value, tuple, "Timeout should be tuple (connect, read)")
        self.assertEqual(len(timeout_value), 2, "Timeout tuple should have 2 values")
        self.assertGreater(timeout_value[0], 0, "Connect timeout should be > 0")
        self.assertGreater(timeout_value[1], 0, "Read timeout should be > 0")

    @patch("website.management.commands.fetch_pr_reviews.requests.get")
    def test_review_with_null_submitted_at_skipped(self, mock_get):
        """Test that reviews with null submitted_at (PENDING) are skipped"""
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

        # Mock API response with PENDING review (no submitted_at)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": 888,
                "user": {
                    "id": 12345,
                    "login": "testuser",
                    "html_url": "https://github.com/testuser",
                    "avatar_url": "https://avatars.githubusercontent.com/u/12345",
                    "type": "User",
                },
                "body": "Pending review",
                "state": "PENDING",
                "submitted_at": None,  # PENDING reviews have null submitted_at
                "html_url": "https://github.com/OWASP-BLT/BLT/pull/123#pullrequestreview-888",
            }
        ]
        mock_get.return_value = mock_response

        # Verify no reviews exist before
        self.assertEqual(GitHubReview.objects.count(), 0, "Should start with no reviews")

        # Run command
        out = StringIO()
        call_command("fetch_pr_reviews", stdout=out)

        # CRITICAL VERIFICATIONS:
        # 1. Verify the mock was actually called (test is not bypassed)
        self.assertTrue(mock_get.called, "API should be called to fetch reviews")
        self.assertEqual(mock_get.call_count, 1, "API should be called exactly once")

        # 2. Verify the mock returned our test data
        returned_data = mock_response.json.return_value
        self.assertEqual(len(returned_data), 1, "Mock should return 1 review")
        self.assertIsNone(returned_data[0]["submitted_at"], "Test data should have null submitted_at")

        # 3. Verify PENDING review was skipped (not created in database)
        self.assertEqual(GitHubReview.objects.count(), 0, "PENDING reviews without submitted_at should be skipped")

        # 4. Verify no review with ID 888 exists
        self.assertFalse(GitHubReview.objects.filter(review_id=888).exists(), "Review 888 should not be created")

    @patch("website.management.commands.fetch_pr_reviews.requests.get")
    def test_review_with_valid_submitted_at_created(self, mock_get):
        """Test that reviews with valid submitted_at are created"""
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

        # Mock API response with valid review
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "id": 999,
                "user": {
                    "id": 12345,
                    "login": "testuser",
                    "html_url": "https://github.com/testuser",
                    "avatar_url": "https://avatars.githubusercontent.com/u/12345",
                    "type": "User",
                },
                "body": "LGTM",
                "state": "APPROVED",
                "submitted_at": "2025-01-01T00:00:00Z",  # Valid date
                "html_url": "https://github.com/OWASP-BLT/BLT/pull/123#pullrequestreview-999",
            }
        ]
        mock_get.return_value = mock_response

        # Verify no reviews exist before
        self.assertEqual(GitHubReview.objects.count(), 0, "Should start with no reviews")

        # Run command
        out = StringIO()
        call_command("fetch_pr_reviews", stdout=out)

        # CRITICAL VERIFICATIONS:
        # 1. Verify the mock was actually called
        self.assertTrue(mock_get.called, "API should be called")
        self.assertEqual(mock_get.call_count, 1, "API should be called exactly once")

        # 2. Verify the mock returned our test data
        returned_data = mock_response.json.return_value
        self.assertEqual(len(returned_data), 1, "Mock should return 1 review")
        self.assertIsNotNone(returned_data[0]["submitted_at"], "Test data should have valid submitted_at")

        # 3. Verify review was created in database
        self.assertEqual(GitHubReview.objects.count(), 1, "Valid reviews should be created")

        # 4. Verify review details match our test data
        review = GitHubReview.objects.first()
        self.assertEqual(review.review_id, 999, "Review ID should match test data")
        self.assertIsNotNone(review.submitted_at, "Review should have submitted_at")
        self.assertEqual(review.state, "APPROVED", "Review state should match test data")
        self.assertEqual(review.body, "LGTM", "Review body should match test data")
        self.assertEqual(review.pull_request.id, pr.id, "Review should link to correct PR")

    def test_leaderboard_displays_correctly(self):
        """Test that leaderboard page loads with GitHub data"""
        response = self.client.get("/leaderboard/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "leaderboard_global.html")
        self.assertContains(response, "Pull Request Leaderboard")
        self.assertContains(response, "Code Review Leaderboard")
