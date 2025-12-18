from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from website.models import UserActivity


class ManagementCommandTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("testuser", "test@example.com", "password")

    def test_cleanup_old_activities(self):
        """Test that old activities are deleted"""
        # Create old activity (100 days ago)
        old_activity = UserActivity.objects.create(user=self.user, activity_type="login")
        old_activity.timestamp = timezone.now() - timedelta(days=100)
        old_activity.save()

        # Create recent activity (10 days ago)
        recent_activity = UserActivity.objects.create(user=self.user, activity_type="login")

        initial_count = UserActivity.objects.count()
        self.assertEqual(initial_count, 2)

        # Run cleanup command
        call_command("aggregate_user_analytics")

        # Old activity should be deleted, recent should remain
        self.assertEqual(UserActivity.objects.count(), 1)
        self.assertTrue(UserActivity.objects.filter(id=recent_activity.id).exists())
        self.assertFalse(UserActivity.objects.filter(id=old_activity.id).exists())
