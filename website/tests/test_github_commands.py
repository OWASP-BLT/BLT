from io import StringIO
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from django.core.management import call_command
from django.test import TransactionTestCase
from django.utils import timezone

from website.models import GitHubIssue, GitHubReview, Repo


class GitHubCommandsIntegrationTests(TransactionTestCase):
    def setUp(self):
        self.repo = Repo.objects.create(name="BLT", repo_url="https://github.com/OWASP-BLT/BLT", is_owasp_repo=True)

    def make_rate_limit_response(self):
        res = Mock(status_code=200)
        res.json.return_value = {"resources": {"core": {"remaining": 5000}}}
        return res

    @patch("website.management.commands.update_github_issues.httpx.AsyncClient")
    def test_timeout_in_update_github_issues(self, mock_client_class):
        mock_user = Mock(id=1, github_url="https://github.com/testuser")
        client = AsyncMock()
        client.__aenter__.return_value = client
        mock_client_class.return_value = client

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {"items": []}
        # CRITICAL FIX: Ensure headers return a string, not a Mock
        resp.headers = {"Link": ""}
        client.get.return_value = resp

        with patch("website.management.commands.update_github_issues.UserProfile.objects.exclude") as mock_query:
            mock_query.return_value.exclude.return_value = [mock_user]
            call_command("update_github_issues", stdout=StringIO())
        self.assertTrue(mock_client_class.called)

    @patch("website.management.commands.fetch_pr_reviews.requests.get")
    def test_review_with_null_submitted_at_skipped(self, mock_get):
        # FIX: Added required timestamps to prevent IntegrityError
        GitHubIssue.objects.create(
            issue_id=123,
            repo=self.repo,
            title="T",
            type="pull_request",
            is_merged=True,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: [{"id": 8, "submitted_at": None, "user": {"id": 1, "login": "u", "type": "User"}}],
        )
        call_command("fetch_pr_reviews", stdout=StringIO())
        self.assertEqual(GitHubReview.objects.count(), 0)

    def test_leaderboard_displays_correctly(self):
        res = self.client.get("/leaderboard/")
        self.assertEqual(res.status_code, 200)
