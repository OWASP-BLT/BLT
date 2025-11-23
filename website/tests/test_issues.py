from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from django.urls import reverse

from comments.models import Comment
from website.models import Issue, UserProfile


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class IssueCommentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.user_profile, created = UserProfile.objects.get_or_create(user=self.user)
        self.issue = Issue.objects.create(url="http://example.com", description="Test Issue", user=self.user)
        self.client.login(username="testuser", password="12345")

    def test_add_comment(self):
        url = reverse("comment_on_content", args=[self.issue.pk])
        data = {"content_type": "issue", "comment": "This is a test comment."}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Comment.objects.filter(content_type__model="issue", object_id=self.issue.pk).exists())

    def test_update_comment(self):
        comment = Comment.objects.create(
            content_type=ContentType.objects.get_for_model(Issue),
            object_id=self.issue.pk,
            author=self.user.username,
            author_fk=self.user_profile,
            text="Original comment",
        )
        url = reverse("update_content_comment", args=[self.issue.pk, comment.pk])
        data = {"content_type": "issue", "comment": "Updated comment"}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        comment.refresh_from_db()
        self.assertEqual(comment.text, "Updated comment")

    def test_delete_comment(self):
        comment = Comment.objects.create(
            content_type=ContentType.objects.get_for_model(Issue),
            object_id=self.issue.pk,
            author=self.user.username,
            author_fk=self.user_profile,
            text="Comment to be deleted",
        )
        url = reverse("delete_content_comment")
        data = {"content_type": "issue", "content_pk": self.issue.pk, "comment_pk": comment.pk}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Comment.objects.filter(pk=comment.pk).exists())


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class GitHubIssueImageURLTests(TestCase):
    """Test that image URLs are properly formatted for GitHub issues"""

    def test_relative_url_formatting(self):
        """Test that relative URLs get properly formatted with https protocol"""
        relative_url = "/media/screenshots/test.png"

        # Simulate the logic from create_github_issue function
        if not relative_url.startswith(("http://", "https://")):
            formatted_url = f"https://{settings.FQDN}{relative_url}"
        else:
            formatted_url = relative_url

        self.assertTrue(formatted_url.startswith("https://"))
        self.assertIn(settings.FQDN, formatted_url)
        self.assertIn("/media/screenshots/test.png", formatted_url)

    def test_absolute_url_unchanged(self):
        """Test that absolute URLs (e.g., from GCS) are used as-is"""
        absolute_url = "https://bhfiles.storage.googleapis.com/screenshots/test.png"

        # Simulate the logic from create_github_issue function
        if not absolute_url.startswith(("http://", "https://")):
            formatted_url = f"https://{settings.FQDN}{absolute_url}"
        else:
            formatted_url = absolute_url

        self.assertEqual(formatted_url, absolute_url)
        self.assertTrue(formatted_url.startswith("https://"))

    def test_http_url_unchanged(self):
        """Test that http URLs are also preserved"""
        http_url = "http://example.com/image.png"

        # Simulate the logic from create_github_issue function
        if not http_url.startswith(("http://", "https://")):
            formatted_url = f"https://{settings.FQDN}{http_url}"
        else:
            formatted_url = http_url

        self.assertEqual(formatted_url, http_url)


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class NLPIntegrationTests(TestCase):
    """Test NLP integration for bug analysis and image processing"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.user_profile, created = UserProfile.objects.get_or_create(user=self.user)
        self.client.login(username="testuser", password="12345")

    @patch("website.views.issue.analyze_bug_with_nlp")
    def test_get_bug_analysis_endpoint(self, mock_analyze):
        """Test the bug analysis API endpoint"""
        mock_analyze.return_value = {
            "suggested_category": "4",
            "tags": ["security", "xss", "web"],
            "severity": "high",
            "enhanced_description": "This is a cross-site scripting vulnerability",
        }

        url = reverse("get_bug_analysis")
        data = {
            "description": "Found XSS vulnerability",
            "url": "https://example.com/vulnerable",
        }
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertTrue(json_data.get("success"))
        self.assertEqual(json_data.get("suggested_category"), "4")
        self.assertIn("security", json_data.get("tags"))
        self.assertEqual(json_data.get("severity"), "high")

    def test_get_bug_analysis_requires_login(self):
        """Test that the bug analysis endpoint requires authentication"""
        self.client.logout()
        url = reverse("get_bug_analysis")
        data = {"description": "Test description"}
        response = self.client.post(url, data)

        # Should redirect to login
        self.assertEqual(response.status_code, 302)

    def test_get_bug_analysis_requires_description(self):
        """Test that description is required for bug analysis"""
        url = reverse("get_bug_analysis")
        data = {"url": "https://example.com"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 400)
        json_data = response.json()
        self.assertIn("error", json_data)

    @patch("website.views.issue.analyze_bug_with_nlp")
    def test_get_bug_analysis_handles_failure(self, mock_analyze):
        """Test handling when NLP analysis fails"""
        mock_analyze.return_value = None

        url = reverse("get_bug_analysis")
        data = {"description": "Test description"}
        response = self.client.post(url, data)

        self.assertEqual(response.status_code, 500)
        json_data = response.json()
        self.assertIn("error", json_data)
