from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from website.models import Issue, UserProfile


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class VoteCountTests(TestCase):
    """Test cases for the vote_count view."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.issue = Issue.objects.create(url="http://example.com", description="Test", user=self.user)
        self.client = Client()

    def test_unauthenticated_redirects_to_login(self):
        """Unauthenticated users should be redirected to login."""
        url = reverse("vote_count", args=[self.issue.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_returns_vote_counts(self):
        """Authenticated user should see vote counts as JSON."""
        self.client.login(username="testuser", password="testpass")
        url = reverse("vote_count", args=[self.issue.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["likes"], 0)
        self.assertEqual(data["dislikes"], 0)

    def test_nonexistent_issue_returns_404(self):
        """Requesting vote count for nonexistent issue should return 404."""
        self.client.login(username="testuser", password="testpass")
        url = reverse("vote_count", args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class FlagIssueTests(TestCase):
    """Test cases for the flag_issue view."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.issue = Issue.objects.create(url="http://example.com", description="Test", user=self.user)
        self.client = Client()

    def test_unauthenticated_redirects_to_login(self):
        """Unauthenticated users should be redirected to login."""
        url = reverse("flag_issue", args=[self.issue.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_flag_issue_toggles_flag(self):
        """Flagging an issue should add a flag, flagging again should remove it."""
        self.client.login(username="testuser", password="testpass")
        url = reverse("flag_issue", args=[self.issue.pk])

        # First flag - should add
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(UserProfile.objects.filter(issue_flaged=self.issue, user=self.user).exists())

        # Second flag - should remove
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(UserProfile.objects.filter(issue_flaged=self.issue, user=self.user).exists())

    def test_nonexistent_issue_returns_404(self):
        """Flagging a nonexistent issue should return 404."""
        self.client.login(username="testuser", password="testpass")
        url = reverse("flag_issue", args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class SaveIssueTests(TestCase):
    """Test cases for the save_issue and unsave_issue views."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.issue = Issue.objects.create(url="http://example.com", description="Test", user=self.user)
        self.client = Client()

    def test_save_unauthenticated_redirects_to_login(self):
        """Unauthenticated users should be redirected to login."""
        url = reverse("save_issue", args=[self.issue.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_save_issue_adds_to_saved(self):
        """Saving an issue should add it to the user's saved list."""
        self.client.login(username="testuser", password="testpass")
        url = reverse("save_issue", args=[self.issue.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"OK")
        self.assertTrue(self.profile.issue_saved.filter(pk=self.issue.pk).exists())

    def test_save_issue_toggles(self):
        """Saving an already-saved issue should remove it."""
        self.client.login(username="testuser", password="testpass")
        url = reverse("save_issue", args=[self.issue.pk])

        # First save
        self.client.get(url)
        self.assertTrue(self.profile.issue_saved.filter(pk=self.issue.pk).exists())

        # Second save - should remove
        response = self.client.get(url)
        self.assertEqual(response.content, b"REMOVED")
        self.assertFalse(self.profile.issue_saved.filter(pk=self.issue.pk).exists())

    def test_unsave_issue(self):
        """Unsaving an issue should remove it from saved list."""
        self.client.login(username="testuser", password="testpass")
        self.profile.issue_saved.add(self.issue)

        url = reverse("unsave_issue", args=[self.issue.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.profile.issue_saved.filter(pk=self.issue.pk).exists())

    def test_save_nonexistent_issue_returns_404(self):
        """Saving a nonexistent issue should return 404."""
        self.client.login(username="testuser", password="testpass")
        url = reverse("save_issue", args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_unsave_nonexistent_issue_returns_404(self):
        """Unsaving a nonexistent issue should return 404."""
        self.client.login(username="testuser", password="testpass")
        url = reverse("unsave_issue", args=[99999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
