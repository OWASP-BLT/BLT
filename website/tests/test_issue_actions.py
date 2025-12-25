from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from website.models import Issue, UserProfile


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class IssueActionsTests(TestCase):
    """Tests for issue like, dislike, flag, and save actions."""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.user_profile = UserProfile.objects.get_or_create(user=self.user)[0]
        self.issue = Issue.objects.create(url="http://example.com", description="Test Issue", user=self.user)
        self.client.login(username="testuser", password="12345")

    def test_like_issue_requires_post(self):
        """Test that like_issue requires POST method."""
        url = reverse("like_issue", args=[self.issue.pk])
        # GET should fail with 405 Method Not Allowed
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

        # POST should succeed
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Success")

        # Verify the issue was liked
        self.assertTrue(self.user_profile.issue_upvoted.filter(pk=self.issue.pk).exists())

    def test_dislike_issue_requires_post(self):
        """Test that dislike_issue requires POST method."""
        url = reverse("dislike_issue", args=[self.issue.pk])
        # GET should fail with 405 Method Not Allowed
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

        # POST should succeed
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "Success")

        # Verify the issue was disliked
        self.assertTrue(self.user_profile.issue_downvoted.filter(pk=self.issue.pk).exists())

    def test_flag_issue_requires_post(self):
        """Test that flag_issue requires POST method."""
        url = reverse("flag_issue", args=[self.issue.pk])
        # GET should fail with 405 Method Not Allowed
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

        # POST should succeed
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)

        # Verify the issue was flagged
        self.assertTrue(self.user_profile.issue_flaged.filter(pk=self.issue.pk).exists())

    def test_save_issue_requires_post(self):
        """Test that save_issue requires POST method."""
        url = reverse("save_issue", args=[self.issue.pk])
        # GET should fail with 405 Method Not Allowed
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

        # POST should succeed
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "OK")

        # Verify the issue was saved
        self.assertTrue(self.user_profile.issue_saved.filter(pk=self.issue.pk).exists())

    def test_unsave_issue_requires_post(self):
        """Test that unsave_issue requires POST method."""
        # First, save the issue
        self.user_profile.issue_saved.add(self.issue)

        url = reverse("unsave_issue", args=[self.issue.pk])
        # GET should fail with 405 Method Not Allowed
        response = self.client.get(url)
        self.assertEqual(response.status_code, 405)

        # POST should succeed
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "OK")

        # Verify the issue was unsaved
        self.assertFalse(self.user_profile.issue_saved.filter(pk=self.issue.pk).exists())

    def test_like_issue_toggle(self):
        """Test that liking an issue twice toggles it."""
        url = reverse("like_issue", args=[self.issue.pk])

        # First like
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(self.user_profile.issue_upvoted.filter(pk=self.issue.pk).exists())

        # Second like (should unlike)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.user_profile.refresh_from_db()
        self.assertFalse(self.user_profile.issue_upvoted.filter(pk=self.issue.pk).exists())

    def test_save_issue_toggle(self):
        """Test that saving an issue twice toggles it."""
        url = reverse("save_issue", args=[self.issue.pk])

        # First save
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "OK")
        self.assertTrue(self.user_profile.issue_saved.filter(pk=self.issue.pk).exists())

        # Second save (should unsave)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "REMOVED")
        self.user_profile.refresh_from_db()
        self.assertFalse(self.user_profile.issue_saved.filter(pk=self.issue.pk).exists())

    def test_like_removes_dislike(self):
        """Test that liking an issue removes a previous dislike."""
        # First dislike
        dislike_url = reverse("dislike_issue", args=[self.issue.pk])
        self.client.post(dislike_url)
        self.assertTrue(self.user_profile.issue_downvoted.filter(pk=self.issue.pk).exists())

        # Then like
        like_url = reverse("like_issue", args=[self.issue.pk])
        self.client.post(like_url)

        # Verify dislike was removed and like was added
        self.user_profile.refresh_from_db()
        self.assertFalse(self.user_profile.issue_downvoted.filter(pk=self.issue.pk).exists())
        self.assertTrue(self.user_profile.issue_upvoted.filter(pk=self.issue.pk).exists())

    def test_dislike_removes_like(self):
        """Test that disliking an issue removes a previous like."""
        # First like
        like_url = reverse("like_issue", args=[self.issue.pk])
        self.client.post(like_url)
        self.assertTrue(self.user_profile.issue_upvoted.filter(pk=self.issue.pk).exists())

        # Then dislike
        dislike_url = reverse("dislike_issue", args=[self.issue.pk])
        self.client.post(dislike_url)

        # Verify like was removed and dislike was added
        self.user_profile.refresh_from_db()
        self.assertFalse(self.user_profile.issue_upvoted.filter(pk=self.issue.pk).exists())
        self.assertTrue(self.user_profile.issue_downvoted.filter(pk=self.issue.pk).exists())

    def test_like_issue_nonexistent_issue(self):
        """Test that like_issue handles non-existent issues gracefully."""
        url = reverse("like_issue", args=[99999])
        response = self.client.post(url)
        # get_object_or_404 returns 404 for non-existent issues
        self.assertEqual(response.status_code, 404)

    def test_dislike_issue_nonexistent_issue(self):
        """Test that dislike_issue handles non-existent issues gracefully."""
        url = reverse("dislike_issue", args=[99999])
        response = self.client.post(url)
        # get_object_or_404 returns 404 for non-existent issues
        self.assertEqual(response.status_code, 404)
