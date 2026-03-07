from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from website.management.commands.update_github_issues import _normalize_github_username
from website.models import Contributor, GitHubIssue, Repo


class UpdateGitHubIssuesCommandTest(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create a test user with GitHub profile
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.user_profile = self.user.userprofile
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

    # ------------------------------------------------------------------ #
    #  Helper: build a standard merged-PR API payload
    #  Use a recent date so the 6-month filter does NOT skip the PR.
    # ------------------------------------------------------------------ #
    def _make_pr_payload(self, repo_org="org1", repo_name="test-repo", pr_number=1):
        # Always use "today" so the PR is never skipped by the 6-month window
        today = timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        return {
            "number": pr_number,
            "title": "Test PR",
            "body": "Test description",
            "state": "closed",
            "created_at": today,
            "updated_at": today,
            "closed_at": today,
            "html_url": f"https://github.com/{repo_org}/{repo_name}/pull/{pr_number}",
            "repository_url": f"https://api.github.com/repos/{repo_org}/{repo_name}",
            "pull_request": {
                "url": f"https://api.github.com/repos/{repo_org}/{repo_name}/pulls/{pr_number}",
                "merged_at": today,  # recent — will NOT be filtered out
            },
            "user": {"url": "https://api.github.com/users/testuser"},
        }

    def _make_mock_get(self, pr_payload):
        """Return a side-effect function that routes mock API calls."""
        mock_pr_response = MagicMock()
        mock_pr_response.json.return_value = {"items": [pr_payload]}
        mock_pr_response.raise_for_status.return_value = None
        mock_pr_response.links = {}

        mock_user_response = MagicMock()
        mock_user_response.json.return_value = {
            "id": 12345,
            "login": "testuser",
            "html_url": "https://github.com/testuser",
            "avatar_url": "https://avatars.githubusercontent.com/u/12345",
            "type": "User",
        }
        mock_user_response.raise_for_status.return_value = None

        mock_reviews_response = MagicMock()
        mock_reviews_response.json.return_value = []
        mock_reviews_response.raise_for_status.return_value = None

        def get_side_effect(url, headers=None, timeout=None):
            if "search/issues" in url:
                return mock_pr_response
            elif "/users/" in url:
                return mock_user_response
            elif "/reviews" in url:
                return mock_reviews_response
            return MagicMock()

        return get_side_effect

    # ------------------------------------------------------------------ #
    #  Existing tests
    # ------------------------------------------------------------------ #

    @patch("website.management.commands.update_github_issues.requests.get")
    def test_command_uses_repo_url_not_name(self, mock_get):
        """Test that the command uses repo_url instead of name to avoid MultipleObjectsReturned errors"""
        mock_get.side_effect = self._make_mock_get(self._make_pr_payload())

        try:
            call_command("update_github_issues")
        except Exception as e:
            self.fail(f"Command raised an exception: {e!s}")

    @patch("website.management.commands.update_github_issues.requests.get")
    def test_command_handles_missing_repo(self, mock_get):
        """Test that the command handles missing repos gracefully"""
        pr_payload = self._make_pr_payload(repo_org="unknown", repo_name="repo")
        mock_get.side_effect = self._make_mock_get(pr_payload)

        try:
            call_command("update_github_issues")
        except Exception as e:
            self.fail(f"Command raised an exception: {e!s}")

    # ------------------------------------------------------------------ #
    #  New tests
    # ------------------------------------------------------------------ #

    @patch("website.management.commands.update_github_issues.requests.get")
    def test_contributions_not_double_counted(self, mock_get):
        """Running the command twice must not increment contributions more than once per unique PR."""
        mock_get.side_effect = self._make_mock_get(self._make_pr_payload())

        call_command("update_github_issues")

        # Reset side effect for second run (mock call count resets automatically)
        mock_get.side_effect = self._make_mock_get(self._make_pr_payload())
        call_command("update_github_issues")

        contributor = Contributor.objects.filter(github_id=12345).first()
        self.assertIsNotNone(contributor, "Contributor should have been created")
        # contributions must be exactly 1, not 2 (idempotency check)
        self.assertEqual(
            contributor.contributions,
            1,
            f"Expected contributions=1 after two syncs, got {contributor.contributions}",
        )

        issue_count = GitHubIssue.objects.filter(issue_id=1, repo=self.repo1).count()
        self.assertEqual(issue_count, 1, "Only one GitHubIssue row should exist for the same PR")

    def test_normalize_github_username_plain_url(self):
        """Standard GitHub profile URL returns the username."""
        self.assertEqual(_normalize_github_username("https://github.com/testuser"), "testuser")

    def test_normalize_github_username_trailing_slash(self):
        """Trailing slash is stripped correctly."""
        self.assertEqual(_normalize_github_username("https://github.com/testuser/"), "testuser")

    def test_normalize_github_username_query_string(self):
        """Query strings (e.g. ?tab=repos) do not corrupt the username."""
        self.assertEqual(
            _normalize_github_username("https://github.com/testuser?tab=repos"),
            "testuser",
        )

    def test_normalize_github_username_empty(self):
        """Empty / None input returns None."""
        self.assertIsNone(_normalize_github_username(""))
        self.assertIsNone(_normalize_github_username(None))

    @patch("website.management.commands.update_github_issues.requests.get")
    def test_command_skips_invalid_github_url(self, mock_get):
        """A UserProfile with an un-parseable GitHub URL is skipped without crashing."""
        self.user_profile.github_url = "https://github.com"  # no username segment
        self.user_profile.save()

        mock_get.return_value = MagicMock(
            json=MagicMock(return_value={"items": []}),
            raise_for_status=MagicMock(return_value=None),
            links={},
        )

        try:
            call_command("update_github_issues")
        except Exception as e:
            self.fail(f"Command raised an exception for invalid URL: {e!s}")
