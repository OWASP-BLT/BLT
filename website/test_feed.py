from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.test import Client, TestCase
from django.urls import reverse

from website.models import Activity, Issue


class ActivityFeedTests(TestCase):
    """Tests for activity feed functionality."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create regular user
        self.user = User.objects.create_user(
            username="testuser", 
            password="testpass123", 
            email="test@example.com"
        )
        
        # Create superuser
        self.superuser = User.objects.create_superuser(
            username="admin", 
            password="adminpass123", 
            email="admin@example.com"
        )
        
        # Create a test issue for activity content
        self.issue = Issue.objects.create(
            user=self.user,
            url="https://example.com/issue",
            description="Test issue for activity",
            status="open",
        )
        
        # Create test activity
        content_type = ContentType.objects.get_for_model(Issue)
        self.activity = Activity.objects.create(
            user=self.user,
            action_type="create",
            title="Created a new bug report",
            description="Test activity description",
            content_type=content_type,
            object_id=self.issue.id,
        )

    def test_feed_page_loads(self):
        """Test that the feed page loads successfully."""
        url = reverse("feed")
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Global Activity Feed")

    def test_activity_displayed_on_feed(self):
        """Test that activities are displayed on the feed."""
        url = reverse("feed")
        response = self.client.get(url)
        
        self.assertContains(response, self.activity.title)
        self.assertContains(response, self.activity.description)
        self.assertContains(response, self.user.username)

    def test_delete_button_not_visible_to_regular_user(self):
        """Test that delete button is not visible to regular users."""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("feed")
        response = self.client.get(url)
        
        # Check that delete button is not present
        self.assertNotContains(response, "deleteActivity")

    def test_delete_button_visible_to_superuser(self):
        """Test that delete button is visible to superusers."""
        self.client.login(username="admin", password="adminpass123")
        url = reverse("feed")
        response = self.client.get(url)
        
        # Check that delete button is present
        self.assertContains(response, "deleteActivity")

    def test_regular_user_cannot_delete_activity(self):
        """Test that regular users cannot delete activities."""
        self.client.login(username="testuser", password="testpass123")
        url = reverse("delete_activity", kwargs={"id": self.activity.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 403)
        # Activity should still exist
        self.assertTrue(Activity.objects.filter(id=self.activity.id).exists())

    def test_superuser_can_delete_activity(self):
        """Test that superusers can delete activities."""
        self.client.login(username="admin", password="adminpass123")
        url = reverse("delete_activity", kwargs={"id": self.activity.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, 200)
        # Activity should be deleted
        self.assertFalse(Activity.objects.filter(id=self.activity.id).exists())

    def test_rss_feed_accessible(self):
        """Test that RSS feed is accessible."""
        url = reverse("activity_feed_rss")
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/rss+xml; charset=utf-8")

    def test_rss_feed_contains_activities(self):
        """Test that RSS feed contains activities."""
        url = reverse("activity_feed_rss")
        response = self.client.get(url)
        
        content = response.content.decode("utf-8")
        self.assertIn(self.activity.title, content)
        self.assertIn(self.user.username, content)

    def test_rss_feed_link_on_page(self):
        """Test that RSS feed link is present on the feed page."""
        url = reverse("feed")
        response = self.client.get(url)
        
        rss_url = reverse("activity_feed_rss")
        self.assertContains(response, rss_url)
        self.assertContains(response, "Subscribe to RSS Feed")
