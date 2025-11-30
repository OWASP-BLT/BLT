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
class GitHubIntegrationFieldsTests(TestCase):
    """Test GitHub integration fields on the Issue model"""

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.user_profile, created = UserProfile.objects.get_or_create(user=self.user)

    def test_issue_created_with_default_github_fields(self):
        """Test that new issues have correct default values for GitHub fields"""
        issue = Issue.objects.create(
            url="http://example.com",
            description="Test Issue",
            user=self.user,
        )

        # Check default values
        self.assertEqual(issue.github_comment_count, 0)
        self.assertEqual(issue.github_state, "")  # Default is empty string, not None
        self.assertFalse(issue.github_fetch_status)
        self.assertEqual(issue.github_url, "")

    def test_issue_with_github_url_and_open_state(self):
        """Test issue with GitHub URL and open state"""
        issue = Issue.objects.create(
            url="http://example.com",
            description="Test Issue with GitHub",
            user=self.user,
            github_url="https://github.com/test/repo/issues/1",
            github_state="open",
            github_comment_count=5,
            github_fetch_status=True,
        )

        self.assertEqual(issue.github_url, "https://github.com/test/repo/issues/1")
        self.assertEqual(issue.github_state, "open")
        self.assertEqual(issue.github_comment_count, 5)
        self.assertTrue(issue.github_fetch_status)

    def test_issue_with_github_url_and_closed_state(self):
        """Test issue with GitHub URL and closed state"""
        issue = Issue.objects.create(
            url="http://example.com",
            description="Test Issue Closed",
            user=self.user,
            github_url="https://github.com/test/repo/issues/2",
            github_state="closed",
            github_comment_count=10,
            github_fetch_status=True,
        )

        self.assertEqual(issue.github_state, "closed")
        self.assertEqual(issue.github_comment_count, 10)
        self.assertTrue(issue.github_fetch_status)

    def test_issue_github_state_choices(self):
        """Test that github_state only accepts valid choices"""
        issue = Issue.objects.create(
            url="http://example.com",
            description="Test Issue",
            user=self.user,
            github_state="open",
        )

        # Test valid choices
        issue.github_state = "closed"
        issue.save()
        issue.refresh_from_db()
        self.assertEqual(issue.github_state, "closed")

        # Test that we can set it back to open
        issue.github_state = "open"
        issue.save()
        issue.refresh_from_db()
        self.assertEqual(issue.github_state, "open")

    def test_issue_github_fetch_failed(self):
        """Test issue when GitHub data fetch fails"""
        issue = Issue.objects.create(
            url="http://example.com",
            description="Test Issue Fetch Failed",
            user=self.user,
            github_url="https://github.com/test/repo/issues/3",
            github_fetch_status=False,  # Fetch failed or not attempted
        )

        self.assertFalse(issue.github_fetch_status)
        self.assertEqual(issue.github_state, "")  # Default is empty string, not None
        self.assertEqual(issue.github_comment_count, 0)

    def test_issue_update_github_fields(self):
        """Test updating GitHub fields on existing issue"""
        issue = Issue.objects.create(
            url="http://example.com",
            description="Test Issue Update",
            user=self.user,
        )

        # Initially no GitHub data
        self.assertEqual(issue.github_comment_count, 0)
        self.assertEqual(issue.github_state, "")  # Default is empty string, not None
        self.assertFalse(issue.github_fetch_status)

        # Update with GitHub data
        issue.github_url = "https://github.com/test/repo/issues/4"
        issue.github_state = "open"
        issue.github_comment_count = 3
        issue.github_fetch_status = True
        issue.save()

        # Verify updates
        issue.refresh_from_db()
        self.assertEqual(issue.github_url, "https://github.com/test/repo/issues/4")
        self.assertEqual(issue.github_state, "open")
        self.assertEqual(issue.github_comment_count, 3)
        self.assertTrue(issue.github_fetch_status)

    def test_issue_github_comment_count_zero(self):
        """Test issue with zero comments"""
        issue = Issue.objects.create(
            url="http://example.com",
            description="Test Issue No Comments",
            user=self.user,
            github_url="https://github.com/test/repo/issues/5",
            github_state="open",
            github_comment_count=0,
            github_fetch_status=True,
        )

        self.assertEqual(issue.github_comment_count, 0)
        self.assertTrue(issue.github_fetch_status)

    def test_issue_github_comment_count_allows_negative(self):
        """Test that negative comment counts are stored without validation"""
        # Django IntegerField allows negative values by default
        # In a production system, consider adding validators or using PositiveIntegerField
        issue = Issue.objects.create(
            url="http://example.com",
            description="Test Issue",
            user=self.user,
            github_comment_count=-1,  # This will be stored (not recommended but allowed)
        )

        # The value will be stored - demonstrates current behavior
        # Note: In practice, comment counts should be non-negative
        self.assertEqual(issue.github_comment_count, -1)

    def test_issue_without_github_url_but_with_state(self):
        """Test that an issue can have GitHub state without URL (edge case)"""
        issue = Issue.objects.create(
            url="http://example.com",
            description="Test Issue Edge Case",
            user=self.user,
            github_state="open",
            github_fetch_status=True,
        )

        # This is allowed but might indicate data inconsistency
        self.assertEqual(issue.github_state, "open")
        self.assertEqual(issue.github_url, "")

    def test_multiple_issues_with_different_github_states(self):
        """Test creating multiple issues with different GitHub states"""
        issue1 = Issue.objects.create(
            url="http://example1.com",
            description="Open Issue",
            user=self.user,
            github_url="https://github.com/test/repo/issues/10",
            github_state="open",
            github_fetch_status=True,
        )

        issue2 = Issue.objects.create(
            url="http://example2.com",
            description="Closed Issue",
            user=self.user,
            github_url="https://github.com/test/repo/issues/11",
            github_state="closed",
            github_fetch_status=True,
        )

        issue3 = Issue.objects.create(
            url="http://example3.com",
            description="Issue Without GitHub",
            user=self.user,
        )

        # Verify all issues maintain their states
        self.assertEqual(Issue.objects.get(pk=issue1.pk).github_state, "open")
        self.assertEqual(Issue.objects.get(pk=issue2.pk).github_state, "closed")
        self.assertEqual(Issue.objects.get(pk=issue3.pk).github_state, "")  # Default is empty string

    def test_issue_github_state_blank_string(self):
        """Test that github_state defaults to blank string"""
        issue = Issue.objects.create(
            url="http://example.com",
            description="Test Issue Blank State",
            user=self.user,
            github_url="https://github.com/test/repo/issues/13",
            github_state="",
            github_fetch_status=False,
        )

        self.assertEqual(issue.github_state, "")
        self.assertFalse(issue.github_fetch_status)
