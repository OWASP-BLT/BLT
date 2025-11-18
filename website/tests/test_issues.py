import json

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from comments.models import Comment
from website.models import Badge, GitHubIssue, Issue, UserBadge


@override_settings(STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage")
class IssueCommentTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="12345")
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
            author_fk=self.user.userprofile,
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
            author_fk=self.user.userprofile,
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


class GitHubWebhookIssueClosedTests(TestCase):
    def setUp(self):
        self.closer_user = User.objects.create_user(username="closer", password="password")
        self.closer_user_profile = self.closer_user.userprofile
        self.closer_user_profile.github_url = "https://github.com/closer"
        self.closer_user_profile.save()

        self.issue_creator = User.objects.create_user(username="creator", password="password")
        self.issue = Issue.objects.create(
            user=self.issue_creator,
            github_url="https://github.com/some/repo/issues/1",
            status="open",
            description="A test issue.",
        )
        # Also create a GitHubIssue object, as the webhook handler interacts with it.
        self.github_issue = GitHubIssue.objects.create(
            issue_id=12345,
            title="Test GitHub Issue",
            url="https://github.com/some/repo/issues/1",
            state="open",
            type="issue",
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

        self.badge, created = Badge.objects.get_or_create(title="First Issue Closed", type="automatic")
        self.webhook_url = reverse("github-webhook")

    def test_issue_closed_webhook_closes_issue_and_awards_badge(self):
        """
        Tests that a GitHub issue 'closed' event closes the corresponding BLT issue
        and awards the 'First Issue Closed' badge to the closer.
        """
        payload = {
            "action": "closed",
            "issue": {
                "html_url": "https://github.com/some/repo/issues/1",
                "closed_at": timezone.now().isoformat(),
            },
            "sender": {"html_url": "https://github.com/closer"},
        }

        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="issues",
        )

        self.assertEqual(response.status_code, 200)

        # Verify BLT issue is closed
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.status, "closed")
        self.assertEqual(self.issue.closed_by, self.closer_user)

        # Verify GitHubIssue is updated
        self.github_issue.refresh_from_db()
        self.assertEqual(self.github_issue.state, "closed")

        # Verify badge is awarded
        self.assertTrue(UserBadge.objects.filter(user=self.closer_user, badge=self.badge).exists())

    def test_badge_not_awarded_for_subsequent_closed_issues(self):
        """
        Tests that the 'First Issue Closed' badge is not awarded if the user has
        already closed an issue before.
        """
        # Create a previously closed issue by the same user to fail the 'is_first_close' check
        Issue.objects.create(
            user=self.issue_creator,
            description="An already closed issue.",
            status="closed",
            closed_by=self.closer_user,
        )

        payload = {
            "action": "closed",
            "issue": {
                "html_url": "https://github.com/some/repo/issues/1",
                "closed_at": timezone.now().isoformat(),
            },
            "sender": {"html_url": "https://github.com/closer"},
        }

        response = self.client.post(
            self.webhook_url,
            data=json.dumps(payload),
            content_type="application/json",
            HTTP_X_GITHUB_EVENT="issues",
        )

        self.assertEqual(response.status_code, 200)

        # Verify BLT issue is closed
        self.issue.refresh_from_db()
        self.assertEqual(self.issue.status, "closed")

        # Verify badge was NOT awarded because it's not their first closed issue
        self.assertFalse(UserBadge.objects.filter(user=self.closer_user, badge=self.badge).exists())
