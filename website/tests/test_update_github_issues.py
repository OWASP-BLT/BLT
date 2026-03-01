"""
Tests for the update_github_issues management command.
"""
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TransactionTestCase
from django.utils import timezone

from website.models import Contributor, GitHubIssue, Repo, UserProfile


class UpdateGitHubIssuesCommandTest(TransactionTestCase):
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create(username="testuser", email="test@example.com")
        self.profile = UserProfile.objects.create(user=self.user, github_url="https://github.com/testuser")
        self.repo = Repo.objects.create(
            name="test-repo", repo_url="https://github.com/OWASP-BLT/test-repo", is_owasp_repo=True
        )

    @patch("website.management.commands.update_github_issues.httpx.AsyncClient")
    def test_command_execution(self, mock_async_client_class):
        """Test that the command executes and saves issues correctly."""
        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        # Explicit headers dictionary prevents test crashing on client.headers.update
        mock_client_instance.headers = {}
        mock_async_client_class.return_value = mock_client_instance

        mock_search_resp = MagicMock()
        mock_search_resp.status_code = 200
        mock_search_resp.json.return_value = {
            "items": [{"pull_request": {"url": "https://api.github.com/repos/OWASP-BLT/test-repo/pulls/1"}}]
        }
        mock_search_resp.headers = {"Link": ""}

        mock_pr_resp = MagicMock()
        mock_pr_resp.status_code = 200
        now_str = timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        mock_pr_resp.json.return_value = {
            "number": 1,
            "title": "Test PR",
            "state": "closed",
            "html_url": "https://github.com/OWASP-BLT/test-repo/pull/1",
            "created_at": now_str,
            "updated_at": now_str,
            "merged_at": now_str,
            "user": {
                "id": 123,
                "login": "testuser",
                "html_url": "https://github.com/testuser",
                "avatar_url": "https://avatars.githubusercontent.com/u/123",
                "type": "User",
            },
            "base": {"repo": {"html_url": "https://github.com/OWASP-BLT/test-repo"}},
        }

        mock_reviews_resp = MagicMock()
        mock_reviews_resp.status_code = 200
        mock_reviews_resp.json.return_value = []

        def get_side_effect(url, *args, **kwargs):
            if "search/issues" in url:
                return mock_search_resp
            elif url.endswith("/reviews"):
                return mock_reviews_resp
            else:
                return mock_pr_resp

        mock_client_instance.get.side_effect = get_side_effect

        out = StringIO()
        call_command("update_github_issues", stdout=out)

        self.assertTrue(Contributor.objects.filter(github_id=123).exists())
        self.assertTrue(GitHubIssue.objects.filter(issue_id=1).exists())

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.merged_pr_count, 1)

    @patch("website.management.commands.update_github_issues.httpx.AsyncClient")
    def test_no_users_with_github(self, mock_async_client_class):
        """Test the command exits early if no users have a GitHub URL."""
        self.profile.github_url = ""
        self.profile.save()

        out = StringIO()
        call_command("update_github_issues", stdout=out)

        self.assertIn("No users with GitHub URLs found", out.getvalue())
        mock_async_client_class.assert_not_called()
