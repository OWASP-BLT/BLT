from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TransactionTestCase

from website.models import Repo


class UpdateGitHubIssuesCommandTest(TransactionTestCase):
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="pass")
        # UserProfile auto-created by post_save signal — use it directly
        self.profile = self.user.userprofile
        # Do NOT set github_url here — individual tests should set it when needed
        self.repo = Repo.objects.create(
            name="test-repo",
            repo_url="https://github.com/OWASP-BLT/test-repo",
            is_owasp_repo=True,
        )

    def test_setUp_creates_profile(self):
        """Verify UserProfile is auto-created and github_url is blank (None or empty) by default"""
        self.assertIsNotNone(self.profile)
        # github_url defaults to None in DB — check it is falsy (blank/unset)
        self.assertFalse(self.profile.github_url)

    def test_command_no_github_users_prints_warning(self):
        """When no users have GitHub URLs, command prints warning and exits"""
        out = StringIO()
        call_command("update_github_issues", stdout=out)
        output = out.getvalue()
        self.assertIn("No users with GitHub URLs found", output)
