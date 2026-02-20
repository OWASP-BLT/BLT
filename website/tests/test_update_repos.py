from unittest.mock import MagicMock, patch

from django.test import TestCase

from website.management.commands.update_repos_dynamic import Command
from website.models import Repo


class UpdateReposDynamicTest(TestCase):
    def setUp(self):
        self.repo = Repo.objects.create(name="Test Repo", repo_url="https://github.com/owner/repo", last_updated=None)
        self.command = Command()

    @patch("website.management.commands.update_repos_dynamic.requests.get")
    def test_update_repo_success(self, mock_get):
        # Mock successful API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "stargazers_count": 10,
            "forks_count": 5,
            "open_issues_count": 2,
            "watchers_count": 3,
            "description": "Test Description",
            "pushed_at": "2023-01-01T00:00:00Z",
        }
        mock_get.return_value = mock_response

        # Run command
        self.command.update_repository(self.repo, skip_issues=True)

        # Reload repo and check fields
        self.repo.refresh_from_db()
        self.assertEqual(self.repo.stars, 10)
        self.assertEqual(self.repo.forks, 5)
        self.assertIsNotNone(self.repo.last_updated)

    @patch("website.management.commands.update_repos_dynamic.requests.get")
    def test_update_repo_failure(self, mock_get):
        # Mock failed API response
        mock_get.side_effect = Exception("Network Error")

        # Command should raise RuntimeError (which handle() would catch)
        with self.assertRaises(RuntimeError):
            self.command.update_repository(self.repo, skip_issues=True)

        # Last updated should NOT change on failure
        self.repo.refresh_from_db()
        self.assertIsNone(self.repo.last_updated)
