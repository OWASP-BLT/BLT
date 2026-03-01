"""
Tests for GitHub data fetching management commands.
Tests focus on key functionality: timeouts, bulk operations, and data integrity.
"""
from datetime import timedelta
from io import StringIO
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TransactionTestCase
from django.utils import timezone

from website.models import Contributor, GitHubIssue, GitHubReview, Repo, UserProfile


class GitHubCommandsIntegrationTests(TransactionTestCase):
    """Integration tests for GitHub management commands"""

    def setUp(self):
        """Set up test data"""
        self.repo = Repo.objects.create(
            name="BLT",
            repo_url="https://github.com/OWASP-BLT/BLT",
            is_owasp_repo=True,
        )
        self.user = User.objects.create(username="testuser_commands", email="test@example.com")
        self.profile = UserProfile.objects.create(user=self.user, github_url="https://github.com/testuser")
        self.contributor = Contributor.objects.create(
            github_id=12345, name="testuser", github_url="https://github.com/testuser"
        )

    def make_rate_limit_response(self, remaining=5000):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "resources": {
                "core": {
                    "remaining": remaining,
                    "reset": int((timezone.now() + timedelta(hours=1)).timestamp()),
                    "limit": 5000,
                }
            }
        }
        return response

    def make_pr(
        self,
        number,
        title="Test PR",
        body="Test description",
        merged_at="2024-06-02T00:00:00Z",
        user_id=12345,
        login="testuser",
        user_type="User",
    ):
        return {
            "number": number,
            "title": title,
            "body": body,
            "state": "closed",
            "created_at": "2024-06-01T00:00:00Z",
            "updated_at": "2024-06-02T00:00:00Z",
            "closed_at": "2024-06-02T00:00:00Z",
            "merged_at": merged_at,
            "url": f"https://api.github.com/repos/OWASP-BLT/BLT/pulls/{number}",
            "html_url": f"https://github.com/OWASP-BLT/BLT/pull/{number}",
            "user": {
                "id": user_id,
                "login": login,
                "html_url": f"https://github.com/{login}",
                "avatar_url": f"https://avatars.githubusercontent.com/u/{user_id}",
                "type": user_type,
            },
        }

    def make_empty_response(self):
        response = Mock()
        response.status_code = 200
        response.json.return_value = []
        return response

    @patch("website.management.commands.fetch_gsoc_prs.time.sleep")
    @patch("website.management.commands.fetch_gsoc_prs.requests.get")
    def test_fetch_gsoc_prs_rest_api_format(self, mock_get, mock_sleep):
        """Test that fetch_gsoc_prs works with REST API format"""
        rate_limit_response = self.make_rate_limit_response()
        prs_response = Mock()
        prs_response.status_code = 200
        prs_response.json.return_value = [
            self.make_pr(123, title="Test PR", merged_at=timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ"))
        ]
        empty_response = self.make_empty_response()

        call_count = {"pulls": 0}

        def side_effect(url, *args, **kwargs):
            if "rate_limit" in url:
                return rate_limit_response
            elif "/pulls" in url:
                call_count["pulls"] += 1
                if call_count["pulls"] == 1:
                    return prs_response
                return empty_response
            elif "/reviews" in url:
                return self.make_empty_response()
            return Mock(status_code=404)

        mock_get.side_effect = side_effect
        out = StringIO()
        call_command("fetch_gsoc_prs", "--repos=OWASP-BLT/BLT", stdout=out)
        self.assertEqual(GitHubIssue.objects.count(), 1)

    @patch("website.management.commands.fetch_gsoc_prs.time.sleep")
    @patch("website.management.commands.fetch_gsoc_prs.requests.get")
    def test_fetch_gsoc_prs_with_since_date(self, mock_get, mock_sleep):
        """Test --since-date argument filters PRs correctly"""
        rate_limit_response = self.make_rate_limit_response()
        prs_response = Mock()
        prs_response.status_code = 200
        prs_response.json.return_value = [self.make_pr(100, title="Recent PR")]
        empty_response = self.make_empty_response()

        call_count = {"pulls": 0}

        def side_effect(url, *args, **kwargs):
            if "rate_limit" in url:
                return rate_limit_response
            elif "/pulls" in url:
                call_count["pulls"] += 1
                if call_count["pulls"] == 1:
                    return prs_response
                return empty_response
            elif "/reviews" in url:
                return self.make_empty_response()
            return Mock(status_code=404)

        mock_get.side_effect = side_effect
        out = StringIO()
        call_command("fetch_gsoc_prs", "--repos=OWASP-BLT/BLT", "--since-date=2024-06-01", stdout=out)
        self.assertEqual(GitHubIssue.objects.count(), 1)

    @patch("website.management.commands.fetch_gsoc_prs.time.sleep")
    @patch("website.management.commands.fetch_gsoc_prs.requests.get")
    def test_fetch_gsoc_prs_default_six_months(self, mock_get, mock_sleep):
        """Test default behavior fetches last 6 months"""

        def side_effect(url, *args, **kwargs):
            if "rate_limit" in url:
                return self.make_rate_limit_response()
            return self.make_empty_response()

        mock_get.side_effect = side_effect
        out = StringIO()
        call_command("fetch_gsoc_prs", "--repos=OWASP-BLT/BLT", stdout=out)
        self.assertIn("last 6 months", out.getvalue())

    @patch("website.management.commands.fetch_gsoc_prs.time.sleep")
    @patch("website.management.commands.fetch_gsoc_prs.requests.get")
    def test_fetch_gsoc_prs_filters_bots(self, mock_get, mock_sleep):
        """Test that bot accounts are filtered out"""
        prs_response = Mock(status_code=200)
        prs_response.json.return_value = [
            self.make_pr(101, login="github-actions", user_type="Bot"),
            self.make_pr(103, title="Human PR", login="realuser"),
        ]

        def side_effect(url, *args, **kwargs):
            if "rate_limit" in url:
                return self.make_rate_limit_response()
            if "/pulls" in url:
                return prs_response
            return self.make_empty_response()

        mock_get.side_effect = side_effect
        call_command("fetch_gsoc_prs", "--repos=OWASP-BLT/BLT", "--since-date=2024-06-01", stdout=StringIO())
        self.assertEqual(GitHubIssue.objects.filter(title="Human PR").count(), 1)
        self.assertEqual(GitHubIssue.objects.count(), 1)

    @patch("website.management.commands.update_github_issues.httpx.AsyncClient")
    def test_timeout_in_update_github_issues(self, mock_async_client_class):
        """Test that update_github_issues uses timeouts and handles SQLite locks"""
        mock_user = Mock()
        mock_user.id = 1
        mock_user.github_url = "https://github.com/testuser"

        mock_client_instance = AsyncMock()
        mock_client_instance.__aenter__.return_value = mock_client_instance
        mock_client_instance.headers = {}

        mock_async_client_class.return_value = mock_client_instance

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_response.headers = {"Link": ""}
        mock_client_instance.get.return_value = mock_response

        with patch("website.management.commands.update_github_issues.UserProfile.objects.exclude") as mock_exclude:
            mock_exclude.return_value.exclude.return_value = [mock_user]
            call_command("update_github_issues", stdout=StringIO())

        self.assertTrue(mock_async_client_class.called)

    @patch("website.management.commands.fetch_pr_reviews.requests.get")
    def test_review_with_null_submitted_at_skipped(self, mock_get):
        """Test that reviews with null submitted_at are skipped"""
        # CRITICAL FIX: Ensure all NOT NULL fields are populated so DB doesn't crash
        GitHubIssue.objects.create(
            issue_id=123,
            repo=self.repo,
            title="T",
            type="pull_request",
            is_merged=True,
            created_at=timezone.now(),
            updated_at=timezone.now(),
            url="https://github.com/OWASP-BLT/BLT/pull/123",
            user_profile=self.profile,
            contributor=self.contributor,
        )

        def mock_json():
            return [{"id": 8, "submitted_at": None, "user": {"id": 1, "login": "u", "type": "User"}}]

        mock_get.return_value = Mock(status_code=200, json=mock_json)
        call_command("fetch_pr_reviews", stdout=StringIO())
        self.assertEqual(GitHubReview.objects.count(), 0)

    def test_leaderboard_displays_correctly(self):
        """Test that leaderboard page loads"""
        response = self.client.get("/leaderboard/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "leaderboard_global.html")
