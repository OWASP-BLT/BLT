from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase

from website.models import Repo, UserProfile


class UpdateGitHubIssuesCommandTest(TestCase):
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.user_profile = UserProfile.objects.get(user=self.user)
        self.user_profile.github_url = "https://github.com/testuser"
        self.user_profile.save()

        self.repo1 = Repo.objects.create(
            name="test-repo",
            repo_url="https://github.com/org1/test-repo",
            slug="org1-test-repo",
        )
        self.repo2 = Repo.objects.create(
            name="test-repo",
            repo_url="https://github.com/org2/test-repo",
            slug="org2-test-repo",
        )

    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    def test_command_uses_repo_url_not_name(self, mock_get):
        """Test that the command uses repo_url instead of name to avoid MultipleObjectsReturned errors"""

        mock_pr_resp = MagicMock(spec=httpx.Response)
        mock_pr_resp.status_code = 200
        mock_pr_resp.json.return_value = {
            "items": [
                {
                    "number": 1,
                    "title": "Test PR",
                    "repository_url": "https://api.github.com/repos/org1/test-repo",
                    "pull_request": {
                        "url": "https://api.github.com/repos/org1/test-repo/pulls/1",
                        "merged_at": "2023-01-01T00:00:00Z",
                    },
                    "user": {"url": "https://api.github.com/users/testuser"},
                }
            ]
        }
        mock_pr_resp.headers = {"Link": ""}

        mock_detail_resp = MagicMock(spec=httpx.Response)
        mock_detail_resp.status_code = 200
        mock_detail_resp.json.return_value = {
            "number": 1,
            "title": "Test PR",
            "state": "closed",
            "html_url": "https://github.com/org1/test-repo/pull/1",
            "created_at": "2023-01-01T00:00:00Z",
            "updated_at": "2023-01-01T00:00:00Z",
            "merged_at": "2023-01-01T00:00:00Z",
            "user": {
                "id": 12345,
                "login": "testuser",
                "html_url": "https://github.com/testuser",
                "avatar_url": "https://avatar.url",
                "type": "User",
            },
            "base": {"repo": {"html_url": "https://github.com/org1/test-repo"}},
        }

        mock_rev_resp = MagicMock(spec=httpx.Response)
        mock_rev_resp.status_code = 200
        mock_rev_resp.json.return_value = []

        def get_side_effect(url, **kwargs):
            if "search/issues" in url:
                return mock_pr_resp
            if "/pulls/" in url and "/reviews" in url:
                return mock_rev_resp
            if "/pulls/" in url:
                return mock_detail_resp
            return MagicMock(spec=httpx.Response, status_code=404)

        mock_get.side_effect = get_side_effect

        try:
            call_command("update_github_issues")
        except Exception as e:
            self.fail(f"Command raised an exception: {e}")

    @patch("httpx.AsyncClient.get", new_callable=AsyncMock)
    def test_command_handles_missing_repo(self, mock_get):
        """Test that the command handles missing repos gracefully (Fixes AttributeError)"""

        mock_pr_resp = MagicMock(spec=httpx.Response)
        mock_pr_resp.status_code = 200
        mock_pr_resp.json.return_value = {
            "items": [{"pull_request": {"url": "https://api.github.com/repos/unknown/repo/pulls/1"}}]
        }
        mock_pr_resp.headers = {"Link": ""}

        mock_detail_resp = MagicMock(spec=httpx.Response)
        mock_detail_resp.status_code = 200
        mock_detail_resp.json.return_value = {"base": {"repo": {"html_url": "https://github.com/unknown/repo"}}}

        mock_rev_resp = MagicMock(spec=httpx.Response)
        mock_rev_resp.status_code = 200
        mock_rev_resp.json.return_value = []

        def get_side_effect(url, **kwargs):
            if "search" in url:
                return mock_pr_resp
            if "reviews" in url:
                return mock_rev_resp
            return mock_detail_resp

        mock_get.side_effect = get_side_effect

        try:
            call_command("update_github_issues")
        except Exception as e:
            self.fail(f"Command raised an exception: {e}")
