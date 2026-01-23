from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from website.models import Adventure, UserAdventureProgress

User = get_user_model()


class AdventureListViewTest(TestCase):
    """Test the AdventureListView to ensure it doesn't raise TypeError."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.adventure = Adventure.objects.create(
            title="Test Adventure",
            slug="test-adventure",
            description="Test description",
            category="owasp_security",
            difficulty="beginner",
            badge_title="Test Badge",
        )

    def test_adventure_list_view_without_user_progress(self):
        """Test that adventure list view works without user progress."""
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("adventure_list"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("adventures", response.context)

    def test_adventure_list_view_with_user_progress(self):
        """Test that adventure list view works with user progress and doesn't raise TypeError."""
        # Create user progress
        UserAdventureProgress.objects.create(user=self.user, adventure=self.adventure)

        # Login and access the view
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("adventure_list"))

        # Should not raise TypeError: Direct assignment to the reverse side of a related set is prohibited
        self.assertEqual(response.status_code, 200)
        self.assertIn("adventures", response.context)

        # Verify the adventure has the current_user_progress attribute
        adventures = list(response.context["adventures"])
        self.assertEqual(len(adventures), 1)
        adventure = adventures[0]
        self.assertTrue(hasattr(adventure, "current_user_progress"))
        self.assertIsNotNone(adventure.current_user_progress)
        self.assertEqual(adventure.current_user_progress.user, self.user)

    def test_adventure_list_view_unauthenticated(self):
        """Test that adventure list view works for unauthenticated users."""
        response = self.client.get(reverse("adventure_list"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("adventures", response.context)
