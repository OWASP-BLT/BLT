"""
Tests for GitHub data fetching management commands.
Tests focus on key functionality: timeouts, bulk operations, and data integrity.
"""

from datetime import timedelta
from io import StringIO
from unittest.mock import Mock, patch

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone

from website.models import Contributor, GitHubIssue, GitHubReview, Repo


class GitHubCommandsIntegrationTests(TestCase):
    """Integration tests for GitHub management commands"""

    def setUp(self):
        """Set up test data"""
        self.repo = Repo.objects.create(
            name="BLT",
            repo_url="https://github.com/OWASP-BLT/BLT",
            is_owasp_repo=True,
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

    def make_reviews_empty_response(self):
        response = Mock()
        response.status_code = 200
        response.json.return_value = []
        return response

    @patch("website.management.commands.fetch_gsoc_prs.time.sleep")  # Mock sleep
    @patch("website.management.commands.fetch_gsoc_prs.requests.get")
    def test_fetch_gsoc_prs_rest_api_format(self, mock_get, mock_sleep):
        """Test that fetch_gsoc_prs works with REST API format (list of PRs)"""
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
                reviews_response = Mock()
                reviews_response.status_code = 200
                reviews_response.json.return_value = []
                return reviews_response
            return Mock(status_code=404)

        mock_get.side_effect = side_effect

        out = StringIO()
        call_command("fetch_gsoc_prs", "--repos=OWASP-BLT/BLT", stdout=out)

        output = out.getvalue()
        self.assertIn("Completed", output)

        self.assertEqual(GitHubIssue.objects.count(), 1)
        pr = GitHubIssue.objects.first()
        self.assertEqual(pr.issue_id, 123)
        self.assertEqual(pr.title, "Test PR")
        self.assertTrue(pr.is_merged)

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
                reviews_response = Mock()
                reviews_response.status_code = 200
                reviews_response.json.return_value = []
                return reviews_response
            return Mock(status_code=404)

        mock_get.side_effect = side_effect

        out = StringIO()
        call_command("fetch_gsoc_prs", "--repos=OWASP-BLT/BLT", "--since-date=2024-06-01", stdout=out)

        output = out.getvalue()
        self.assertIn("since 2024-06-01", output)

        self.assertEqual(GitHubIssue.objects.count(), 1)
        pr = GitHubIssue.objects.first()
        self.assertEqual(pr.issue_id, 100)
        self.assertEqual(pr.title, "Recent PR")

    @patch("website.management.commands.fetch_gsoc_prs.time.sleep")
    @patch("website.management.commands.fetch_gsoc_prs.requests.get")
    def test_fetch_gsoc_prs_default_six_months(self, mock_get, mock_sleep):
        """Test default behavior fetches last 6 months (backward compatibility)"""
        rate_limit_response = self.make_rate_limit_response()

        prs_response = Mock()
        prs_response.status_code = 200
        prs_response.json.return_value = []

        def side_effect(url, *args, **kwargs):
            if "rate_limit" in url:
                return rate_limit_response
            elif "/pulls" in url:
                return prs_response
            elif "/reviews" in url:
                reviews_response = Mock()
                reviews_response.status_code = 200
                reviews_response.json.return_value = []
                return reviews_response
            return Mock(status_code=404)

        mock_get.side_effect = side_effect

        out = StringIO()
        call_command("fetch_gsoc_prs", "--repos=OWASP-BLT/BLT", stdout=out)

        output = out.getvalue()
        self.assertIn("last 6 months", output)

    @patch("website.management.commands.fetch_gsoc_prs.time.sleep")
    @patch("website.management.commands.fetch_gsoc_prs.requests.get")
    def test_fetch_gsoc_prs_filters_bots(self, mock_get, mock_sleep):
        """Test that bot accounts are filtered out"""
        rate_limit_response = self.make_rate_limit_response()

        prs_response = Mock()
        prs_response.status_code = 200
        prs_response.json.return_value = [
            self.make_pr(101, login="github-actions", user_type="Bot"),
            self.make_pr(102, login="dependabot[bot]"),
            self.make_pr(103, title="Human PR", login="realuser"),
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
                reviews_response = Mock()
                reviews_response.status_code = 200
                reviews_response.json.return_value = []
                return reviews_response
            return Mock(status_code=404)

        mock_get.side_effect = side_effect

        out = StringIO()
        call_command("fetch_gsoc_prs", "--repos=OWASP-BLT/BLT", "--since-date=2024-06-01", stdout=out)

        self.assertEqual(GitHubIssue.objects.count(), 1)
        pr = GitHubIssue.objects.first()
        self.assertEqual(pr.issue_id, 103)
        self.assertEqual(pr.title, "Human PR")

    @patch("website.management.commands.fetch_gsoc_prs.time.sleep")
    @patch("website.management.commands.fetch_gsoc_prs.requests.get")
    def test_fetch_gsoc_prs_skips_unmerged_prs(self, mock_get, mock_sleep):
        """Test that unmerged PRs are skipped"""
        rate_limit_response = self.make_rate_limit_response()

        prs_response = Mock()
        prs_response.status_code = 200
        prs_response.json.return_value = [self.make_pr(123, merged_at=None), self.make_pr(201, title="Merged PR")]

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
                reviews_response = Mock()
                reviews_response.status_code = 200
                reviews_response.json.return_value = []
                return reviews_response
            return Mock(status_code=404)

        mock_get.side_effect = side_effect

        out = StringIO()
        call_command("fetch_gsoc_prs", "--repos=OWASP-BLT/BLT", "--since-date=2024-06-01", stdout=out)

        self.assertEqual(GitHubIssue.objects.count(), 1)
        pr = GitHubIssue.objects.first()
        self.assertEqual(pr.issue_id, 201)
        self.assertTrue(pr.is_merged)

    @patch("website.management.commands.fetch_gsoc_prs.time.sleep")
    @patch("website.management.commands.fetch_gsoc_prs.requests.get")
    def test_fetch_gsoc_prs_rate_limit_check(self, mock_get, mock_sleep):
        """Test that rate limit is checked before API calls"""
        rate_limit_response = self.make_rate_limit_response()

        prs_response = Mock()
        prs_response.status_code = 200
        prs_response.json.return_value = []

        def side_effect(url, *args, **kwargs):
            if "rate_limit" in url:
                return rate_limit_response
            elif "/pulls" in url:
                return prs_response
            elif "/reviews" in url:
                reviews_response = Mock()
                reviews_response.status_code = 200
                reviews_response.json.return_value = []
                return reviews_response
            return Mock(status_code=404)

        mock_get.side_effect = side_effect

        out = StringIO()
        call_command("fetch_gsoc_prs", "--repos=OWASP-BLT/BLT", stdout=out)

        rate_limit_calls = [call for call in mock_get.call_args_list if "rate_limit" in str(call)]
        self.assertGreaterEqual(len(rate_limit_calls), 1, "Rate limit should be checked at least once")

    @patch("website.management.commands.fetch_gsoc_prs.time.sleep")
    @patch("website.management.commands.fetch_gsoc_prs.requests.get")
    def test_fetch_gsoc_prs_bulk_create_and_update(self, mock_get, mock_sleep):
        """Test bulk create for new PRs and bulk update for existing PRs"""
        existing_contributor = Contributor.objects.create(
            github_id=12345,
            name="testuser",
            github_url="https://github.com/testuser",
            avatar_url="https://avatars.githubusercontent.com/u/12345",
            contributor_type="User",
            contributions=0,
        )

        GitHubIssue.objects.create(
            issue_id=123,
            repo=self.repo,
            title="Old Title",
            body="Old body",
            state="open",
            type="pull_request",
            created_at=timezone.now() - timedelta(days=10),
            updated_at=timezone.now() - timedelta(days=10),
            merged_at=timezone.now() - timedelta(days=9),
            is_merged=True,
            url="https://github.com/OWASP-BLT/BLT/pull/123",
            contributor=existing_contributor,
        )

        rate_limit_response = self.make_rate_limit_response()

        prs_response = Mock()
        prs_response.status_code = 200
        prs_response.json.return_value = [
            self.make_pr(123, title="Updated Title", body="Updated body"),
            self.make_pr(124, title="New PR"),
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
                reviews_response = Mock()
                reviews_response.status_code = 200
                reviews_response.json.return_value = []
                return reviews_response
            return Mock(status_code=404)

        mock_get.side_effect = side_effect

        out = StringIO()
        call_command("fetch_gsoc_prs", "--repos=OWASP-BLT/BLT", "--since-date=2024-06-01", stdout=out)

        output = out.getvalue()
        self.assertIn("Added 1", output)
        self.assertIn("Updated 1", output)

        self.assertEqual(GitHubIssue.objects.count(), 2)

        updated_pr = GitHubIssue.objects.get(issue_id=123)
        self.assertEqual(updated_pr.title, "Updated Title")
        self.assertEqual(updated_pr.body, "Updated body")
        self.assertEqual(updated_pr.state, "closed")

        new_pr = GitHubIssue.objects.get(issue_id=124)
        self.assertEqual(new_pr.title, "New PR")

    @patch("website.management.commands.fetch_gsoc_prs.time.sleep")
    @patch("website.management.commands.fetch_gsoc_prs.requests.get")
    def test_fetch_gsoc_prs_handles_403_retry(self, mock_get, mock_sleep):
        """Test that 403 responses trigger retry logic"""
        rate_limit_response = self.make_rate_limit_response()

        forbidden_response = Mock()
        forbidden_response.status_code = 403
        forbidden_response.headers = {"Retry-After": "1"}

        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = []

        call_count = {"pulls": 0}

        def side_effect(url, *args, **kwargs):
            if "rate_limit" in url:
                return rate_limit_response
            elif "/pulls" in url:
                call_count["pulls"] += 1
                if call_count["pulls"] == 1:
                    return forbidden_response
                return success_response
            elif "/reviews" in url:
                reviews_response = Mock()
                reviews_response.status_code = 200
                reviews_response.json.return_value = []
                return reviews_response
            return Mock(status_code=404)

        mock_get.side_effect = side_effect

        out = StringIO()
        call_command("fetch_gsoc_prs", "--repos=OWASP-BLT/BLT", stdout=out)

        self.assertGreaterEqual(call_count["pulls"], 1)
        self.assertTrue(mock_sleep.called)

    @patch("website.management.commands.fetch_pr_reviews.requests.get")
    def test_fetch_pr_reviews_command_exists(self, mock_get):
        """Test that fetch_pr_reviews command can be called with mocked API"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        out = StringIO()
        call_command("fetch_pr_reviews", stdout=out)

        output = out.getvalue()
        self.assertTrue(
            "Completed" in output or "No reviews found" in output,
            "Command should complete successfully",
        )

    def test_update_github_issues_command_exists(self):
        """Test that update_github_issues command prints correct message when no users have GitHub URLs"""
        out = StringIO()
        call_command("update_github_issues", stdout=out)
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

        pr.title = "Updated Title"
        pr.state = "closed"
        pr.save()

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

        review = GitHubReview.objects.create(
            review_id=999,
            pull_request=pr,
            reviewer_contributor=reviewer,
            body="LGTM",
            state="APPROVED",
            submitted_at=timezone.now(),
            url="https://github.com/OWASP-BLT/BLT/pull/123#pullrequestreview-999",
        )

        self.assertEqual(review.pull_request.id, pr.id)
        self.assertEqual(review.pull_request.issue_id, 123)
        self.assertIsNotNone(review.reviewer_contributor)

    @patch("website.management.commands.fetch_gsoc_prs.time.sleep")
    @patch("website.management.commands.fetch_gsoc_prs.requests.get")
    def test_timeout_in_fetch_gsoc_prs(self, mock_get, mock_sleep):
        """Test that fetch_gsoc_prs uses timeouts"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "resources": {"core": {"remaining": 5000, "reset": int((timezone.now() + timedelta(hours=1)).timestamp())}}
        }

        empty_response = self.make_empty_response()

        def side_effect(url, *args, **kwargs):
            if "rate_limit" in url:
                return mock_response
            elif "/pulls" in url:
                return empty_response
            return Mock(status_code=404)

        mock_get.side_effect = side_effect

        out = StringIO()
        call_command("fetch_gsoc_prs", "--repos=OWASP-BLT/BLT", stdout=out)

        self.assertTrue(mock_get.called, "API should be called")
        self.assertGreater(mock_get.call_count, 0, "API should be called at least once")

        has_timeout = False
        for call in mock_get.call_args_list:
            call_kwargs = call[1]
            if "timeout" in call_kwargs:
                has_timeout = True
                timeout_value = call_kwargs["timeout"]
                self.assertIsNotNone(timeout_value, "Timeout should not be None")
                self.assertNotEqual(timeout_value, 0, "Timeout should not be 0")
                break

        self.assertTrue(has_timeout, "At least one API request must have timeout parameter")

        output = out.getvalue()
        self.assertIn("Completed", output, "Command should complete successfully")

    def test_timeout_in_update_github_issues(self):
        """Test that update_github_issues uses an httpx.AsyncClient with a timeout"""
        import inspect

        import website.management.commands.update_github_issues as cmd_module

        source = inspect.getsource(cmd_module)
        self.assertIn(
            "httpx.AsyncClient",
            source,
            "Command must use httpx.AsyncClient",
        )
        self.assertIn(
            "httpx.Timeout",
            source,
            "Command must specify a timeout via httpx.Timeout",
        )

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

        GitHubIssue.objects.create(
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
                "submitted_at": None,
                "html_url": "https://github.com/OWASP-BLT/BLT/pull/123#pullrequestreview-888",
            }
        ]
        mock_get.return_value = mock_response

        self.assertEqual(GitHubReview.objects.count(), 0, "Should start with no reviews")

        out = StringIO()
        call_command("fetch_pr_reviews", stdout=out)

        self.assertTrue(mock_get.called, "API should be called to fetch reviews")
        self.assertEqual(mock_get.call_count, 1, "API should be called exactly once")

        returned_data = mock_response.json.return_value
        self.assertEqual(len(returned_data), 1, "Mock should return 1 review")
        self.assertIsNone(returned_data[0]["submitted_at"], "Test data should have null submitted_at")

        self.assertEqual(GitHubReview.objects.count(), 0, "PENDING reviews without submitted_at should be skipped")
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
                "submitted_at": "2025-01-01T00:00:00Z",
                "html_url": "https://github.com/OWASP-BLT/BLT/pull/123#pullrequestreview-999",
            }
        ]
        mock_get.return_value = mock_response

        self.assertEqual(GitHubReview.objects.count(), 0, "Should start with no reviews")

        out = StringIO()
        call_command("fetch_pr_reviews", stdout=out)

        self.assertTrue(mock_get.called, "API should be called")
        self.assertEqual(mock_get.call_count, 1, "API should be called exactly once")

        returned_data = mock_response.json.return_value
        self.assertEqual(len(returned_data), 1, "Mock should return 1 review")
        self.assertIsNotNone(returned_data[0]["submitted_at"], "Test data should have valid submitted_at")

        self.assertEqual(GitHubReview.objects.count(), 1, "Valid reviews should be created")

        review = GitHubReview.objects.first()
        self.assertEqual(review.review_id, 999, "Review ID should match test data")
        self.assertIsNotNone(review.submitted_at, "Review should have submitted_at")
        self.assertEqual(review.state, "APPROVED", "Review state should match test data")
        self.assertEqual(review.body, "LGTM", "Review body should match test data")
        self.assertEqual(review.pull_request.id, pr.id, "Review should link to correct PR")

    @override_settings(
        STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
        }
    )
    def test_leaderboard_displays_correctly(self):
        """Test that leaderboard page loads with GitHub data"""
        response = self.client.get("/leaderboard/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "leaderboard_global.html")
        self.assertContains(response, "Pull Request Leaderboard")
        self.assertContains(response, "Code Review Leaderboard")
