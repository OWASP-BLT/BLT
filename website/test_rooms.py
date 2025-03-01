from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from website.models import Room

User = get_user_model()


class RoomsViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        # Create a test user
        self.user = User.objects.create_user(username="testuser", password="12345")
        # Create a test room
        self.room = Room.objects.create(name="Test Room", description="A test room for testing", admin=self.user)

    def test_rooms_list_view(self):
        """Test that the discussion rooms page loads successfully"""
        response = self.client.get(reverse("rooms_list"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "rooms_list.html")
        self.assertContains(response, "Test Room")
        self.assertContains(response, "Discussion Rooms")

        # Check context data
        self.assertIn("rooms", response.context)
        self.assertIn("form", response.context)
        self.assertIn("breadcrumbs", response.context)

        # Verify our test room is in the queryset
        rooms = response.context["rooms"]
        self.assertTrue(any(room.name == "Test Room" for room in rooms))
