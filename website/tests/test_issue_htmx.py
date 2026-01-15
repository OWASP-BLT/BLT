from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse

from website.models import Issue, UserProfile


class IssueHTMXTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.user_profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.issue = Issue.objects.create(url="https://example.com/bug", description="Test bug", user=self.user)
        self.client.login(username="testuser", password="testpass123")

    def test_like_issue_htmx(self):
        """Test HTMX like request"""
        response = self.client.post(
            reverse("like_issue", kwargs={"issue_pk": self.issue.pk}),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"like-section", response.content)
        # Verify user profile was updated
        self.user_profile.refresh_from_db()
        self.assertTrue(self.user_profile.issue_upvoted.filter(pk=self.issue.pk).exists())

    def test_like_issue_toggle_off(self):
        """Test toggling like off"""
        # First like
        self.user_profile.issue_upvoted.add(self.issue)
        # Then unlike
        response = self.client.post(
            reverse("like_issue", kwargs={"issue_pk": self.issue.pk}),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.user_profile.refresh_from_db()
        self.assertFalse(self.user_profile.issue_upvoted.filter(pk=self.issue.pk).exists())

    def test_dislike_removes_like(self):
        """Test that disliking removes existing like"""
        # First like
        self.user_profile.issue_upvoted.add(self.issue)
        # Then dislike
        response = self.client.post(
            reverse("dislike_issue", kwargs={"issue_pk": self.issue.pk}),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.user_profile.refresh_from_db()
        self.assertFalse(self.user_profile.issue_upvoted.filter(pk=self.issue.pk).exists())
        self.assertTrue(self.user_profile.issue_downvoted.filter(pk=self.issue.pk).exists())

    def test_flag_issue_htmx(self):
        """Test HTMX flag request"""
        response = self.client.post(
            reverse("flag_issue", kwargs={"issue_pk": self.issue.pk}),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.user_profile.refresh_from_db()
        self.assertTrue(self.user_profile.issue_flaged.filter(pk=self.issue.pk).exists())

    def test_save_issue_htmx(self):
        """Test HTMX save request"""
        response = self.client.post(
            reverse("save_issue", kwargs={"issue_pk": self.issue.pk}),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"bookmark-section", response.content)
        self.user_profile.refresh_from_db()
        self.assertTrue(self.user_profile.issue_saved.filter(pk=self.issue.pk).exists())

    def test_like_requires_login(self):
        """Test that like requires authentication"""
        self.client.logout()
        response = self.client.post(
            reverse("like_issue", kwargs={"issue_pk": self.issue.pk}),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_like_requires_post(self):
        """Test that like only accepts POST"""
        response = self.client.get(
            reverse("like_issue", kwargs={"issue_pk": self.issue.pk}),
        )
        self.assertEqual(response.status_code, 405)  # Method not allowed

    def test_like_rate_limit(self):
        """Test that like action is rate limited"""
        cache.clear()
        # Make 10 requests (should succeed)
        for _ in range(10):
            response = self.client.post(
                reverse("like_issue", kwargs={"issue_pk": self.issue.pk}),
                HTTP_HX_REQUEST="true",
            )
            self.assertEqual(response.status_code, 200)

        # 11th request should be rate limited
        response = self.client.post(
            reverse("like_issue", kwargs={"issue_pk": self.issue.pk}),
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 429)
        self.assertIn(b"Rate limit exceeded", response.content)
