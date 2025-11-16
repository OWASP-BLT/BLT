from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import AICommentaryTemplate, GitHubEvent, Leaderboard, MonitoredEntity, UserChannel


class MonitoredEntityTestCase(TestCase):
    def setUp(self):
        self.entity = MonitoredEntity.objects.create(
            name="test/repo", scope="repository", github_url="https://github.com/test/repo", is_active=True
        )

    def test_monitored_entity_creation(self):
        """Test creating a monitored entity"""
        self.assertEqual(self.entity.name, "test/repo")
        self.assertEqual(self.entity.scope, "repository")
        self.assertTrue(self.entity.is_active)

    def test_monitored_entity_str(self):
        """Test string representation"""
        self.assertEqual(str(self.entity), "test/repo (repository)")


class GitHubEventTestCase(TestCase):
    def setUp(self):
        self.entity = MonitoredEntity.objects.create(
            name="test/repo", scope="repository", github_url="https://github.com/test/repo"
        )
        self.event = GitHubEvent.objects.create(
            monitored_entity=self.entity, event_type="star", event_data={"count": 5}, commentary_text="Test commentary"
        )

    def test_event_creation(self):
        """Test creating a GitHub event"""
        self.assertEqual(self.event.event_type, "star")
        self.assertEqual(self.event.event_data["count"], 5)
        self.assertFalse(self.event.processed)

    def test_event_commentary(self):
        """Test event has commentary"""
        self.assertEqual(self.event.commentary_text, "Test commentary")


class LeaderboardTestCase(TestCase):
    def setUp(self):
        self.entity = MonitoredEntity.objects.create(
            name="test/repo", scope="repository", github_url="https://github.com/test/repo"
        )
        self.leaderboard = Leaderboard.objects.create(
            monitored_entity=self.entity, metric_type="stars", current_value=100, previous_value=95, rank=1
        )

    def test_leaderboard_creation(self):
        """Test creating a leaderboard entry"""
        self.assertEqual(self.leaderboard.current_value, 100)
        self.assertEqual(self.leaderboard.rank, 1)

    def test_leaderboard_change(self):
        """Test calculating value change"""
        change = self.leaderboard.current_value - self.leaderboard.previous_value
        self.assertEqual(change, 5)


class UserChannelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.channel = UserChannel.objects.create(
            user=self.user, name="My Channel", description="Test channel", is_public=True
        )

    def test_channel_creation(self):
        """Test creating a user channel"""
        self.assertEqual(self.channel.name, "My Channel")
        self.assertTrue(self.channel.is_public)

    def test_channel_str(self):
        """Test string representation"""
        self.assertEqual(str(self.channel), "testuser's My Channel")


class SportscasterViewsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")

    def test_api_leaderboard(self):
        """Test leaderboard API endpoint"""
        response = self.client.get(reverse("sportscaster:api_leaderboard"))
        self.assertEqual(response.status_code, 200)

    def test_api_events(self):
        """Test events API endpoint"""
        response = self.client.get(reverse("sportscaster:api_events"))
        self.assertEqual(response.status_code, 200)
