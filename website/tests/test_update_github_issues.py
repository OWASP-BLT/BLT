from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from website.models import Repo, UserProfile


class UpdateGitHubIssuesCommandTest(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create a test user with GitHub profile
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.user_profile = UserProfile.objects.get(user=self.user)
        self.user_profile.github_url = "https://github.com/testuser"
        self.user_profile.save()

        # Create test repositories with unique URLs
        self.repo1 = Repo.objects.create(
            name="test-repo",
            repo_url="https://github.com/org1/test-repo",
            slug="org1-test-repo",
        )
        self.repo2 = Repo.objects.create(
            name="test-repo",  # Same name as repo1
            repo_url="https://github.com/org2/test-repo",  # Different URL
            slug="org2-test-repo",
        )
        self.repo3 = Repo.objects.create(
            name="another-repo",
            repo_url="https://github.com/org1/another-repo",
            slug="org1-another-repo",
        )

    @patch("website.management.commands.update_github_issues.requests.get")
    def test_command_uses_repo_url_not_name(self, mock_get):
        """Test that the command uses repo_url instead of name to avoid MultipleObjectsReturned errors"""
        # Mock the GitHub API response for user's PRs
        mock_pr_response = MagicMock()
        mock_pr_response.json.return_value = {
            "items": [
                {
                    "number": 1,
                    "title": "Test PR",
                    "body": "Test description",
                    "state": "open",
                    "created_at": "2023-01-01T00:00:00Z",
                    "updated_at": "2023-01-02T00:00:00Z",
                    "closed_at": None,
                    "html_url": "https://github.com/org1/test-repo/pull/1",
                    "repository_url": "https://api.github.com/repos/org1/test-repo",
                    "pull_request": {"url": "https://api.github.com/repos/org1/test-repo/pulls/1", "merged_at": None},
                    "user": {"url": "https://api.github.com/users/testuser"},
                }
            ]
        }
        mock_pr_response.raise_for_status.return_value = None
        mock_pr_response.links = {}

        # Mock the user API response
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {
            "id": 12345,
            "login": "testuser",
            "html_url": "https://github.com/testuser",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345",
            "type": "User",
        }
        mock_user_response.raise_for_status.return_value = None

        # Mock the reviews API response
        mock_reviews_response = MagicMock()
        mock_reviews_response.json.return_value = []
        mock_reviews_response.raise_for_status.return_value = None

        # Set up the mock to return different responses based on URL
        def get_side_effect(url, headers=None, timeout=None):
            if "search/issues" in url:
                return mock_pr_response
            elif "/users/" in url:
                return mock_user_response
            elif "/reviews" in url:
                return mock_reviews_response
            return MagicMock()

        mock_get.side_effect = get_side_effect

        # Run the command - should not raise MultipleObjectsReturned error
        try:
            call_command("update_github_issues")
        except Exception as e:
            self.fail(f"Command raised an exception: {str(e)}")

    @patch("website.management.commands.update_github_issues.requests.get")
    def test_command_handles_missing_repo(self, mock_get):
        """Test that the command handles missing repos gracefully"""
        # Mock the GitHub API response for a PR from a repo not in our database
        mock_pr_response = MagicMock()
        mock_pr_response.json.return_value = {
            "items": [
                {
                    "number": 1,
                    "title": "Test PR",
                    "body": "Test description",
                    "state": "open",
                    "created_at": "2023-01-01T00:00:00Z",
                    "updated_at": "2023-01-02T00:00:00Z",
                    "closed_at": None,
                    "html_url": "https://github.com/unknown/repo/pull/1",
                    "repository_url": "https://api.github.com/repos/unknown/repo",
                    "pull_request": {"url": "https://api.github.com/repos/unknown/repo/pulls/1", "merged_at": None},
                    "user": {"url": "https://api.github.com/users/testuser"},
                }
            ]
        }
        mock_pr_response.raise_for_status.return_value = None
        mock_pr_response.links = {}

        # Mock the user API response (not needed but set up for consistency)
        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {
            "id": 12345,
            "login": "testuser",
            "html_url": "https://github.com/testuser",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345",
            "type": "User",
        }
        mock_user_response.raise_for_status.return_value = None

        # Set up the mock to return different responses based on URL
        def get_side_effect(url, headers=None, timeout=None):
            if "search/issues" in url:
                return mock_pr_response
            elif "/users/" in url:
                return mock_user_response
            return MagicMock()

        mock_get.side_effect = get_side_effect

        # Run the command - should handle missing repo gracefully
        try:
            call_command("update_github_issues")
        except Exception as e:
            self.fail(f"Command raised an exception: {str(e)}")
