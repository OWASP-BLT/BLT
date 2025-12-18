from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from comments.models import Comment
from website.models import Domain, Issue, Organization, UserActivity, UserProfile


class ActivitySignalsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("testuser", "test@example.com", "password")
        self.user_profile, _ = UserProfile.objects.get_or_create(user=self.user)
        self.org = Organization.objects.create(name="Test Org", url="https://test.com")
        self.domain = Domain.objects.create(name="test.com", organization=self.org, url="https://test.com")

    def test_bug_report_signal_creates_activity(self):
        """Test that creating an Issue triggers activity logging"""
        initial_count = UserActivity.objects.count()

        issue = Issue.objects.create(
            user=self.user, domain=self.domain, description="Test bug", url="https://test.com/bug"
        )

        # Check that activity was created
        self.assertEqual(UserActivity.objects.count(), initial_count + 1)

        # Verify activity details
        activity = UserActivity.objects.latest("timestamp")
        self.assertEqual(activity.user, self.user)
        self.assertEqual(activity.organization, self.org)
        self.assertEqual(activity.activity_type, "bug_report")
        self.assertEqual(activity.metadata["issue_id"], issue.id)

    def test_bug_comment_signal_creates_activity(self):
        """Test that creating a Comment on Issue triggers activity logging"""
        issue = Issue.objects.create(
            user=self.user, domain=self.domain, description="Test bug", url="https://test.com/bug"
        )

        initial_count = UserActivity.objects.count()

        # Create comment on issue
        content_type = ContentType.objects.get_for_model(Issue)
        comment = Comment.objects.create(
            author=self.user.username,
            author_fk=self.user_profile,
            text="Test comment",
            content_type=content_type,
            object_id=issue.id,
        )

        # Check that activity was created (1 from issue creation + 1 from comment)
        self.assertGreater(UserActivity.objects.count(), initial_count)

        # Verify comment activity
        comment_activity = UserActivity.objects.filter(activity_type="bug_comment").latest("timestamp")
        self.assertEqual(comment_activity.user, self.user)
        self.assertEqual(comment_activity.activity_type, "bug_comment")
        self.assertEqual(comment_activity.metadata["comment_id"], comment.id)
