import json

from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.test import Client, TestCase, TransactionTestCase
from django.urls import reverse

from blt.routing import application
from website.models import Message, Room

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


class ChatConsumerTests(TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="12345")
        self.room = Room.objects.create(name="Test Room", description="A test room", admin=self.user)
        self.message = Message.objects.create(
            room=self.room, user=self.user, username=self.user.username, content="Test message"
        )

    async def test_logged_in_user_add_and_remove_reaction(self):
        """Test that a logged-in user can add and remove a reaction."""
        communicator = WebsocketCommunicator(application, f"/ws/discussion-rooms/chat/{self.room.id}/")
        communicator.scope["user"] = self.user
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Consume connection status message
        response = await communicator.receive_from()
        self.assertEqual(json.loads(response), {"type": "connection_status", "status": "connected"})

        # Add reaction
        await communicator.send_to(
            text_data=json.dumps({"type": "add_reaction", "message_id": self.message.id, "emoji": "👍"})
        )

        response = await communicator.receive_from()
        response_data = json.loads(response)
        self.assertEqual(response_data["type"], "reaction_update")
        self.assertEqual(response_data["message_id"], self.message.id)
        self.assertIn("👍", response_data["reactions"])
        self.assertIn(self.user.username, response_data["reactions"]["👍"])

        await self.message.arefresh_from_db()
        self.assertIn("👍", self.message.reactions)
        self.assertIn(self.user.username, self.message.reactions["👍"])

        # Remove reaction
        await communicator.send_to(
            text_data=json.dumps({"type": "add_reaction", "message_id": self.message.id, "emoji": "👍"})
        )

        response = await communicator.receive_from()
        response_data = json.loads(response)
        self.assertEqual(response_data["type"], "reaction_update")
        self.assertEqual(response_data["reactions"], {})

        await self.message.arefresh_from_db()
        self.assertEqual(self.message.reactions, {})

        await communicator.disconnect()

    async def test_anonymous_user_add_and_remove_reaction(self):
        """Test that an anonymous user can add and remove a reaction."""
        communicator = WebsocketCommunicator(application, f"/ws/discussion-rooms/chat/{self.room.id}/")
        communicator.scope["user"] = AnonymousUser()
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Consume connection status message
        response = await communicator.receive_from()
        self.assertEqual(json.loads(response), {"type": "connection_status", "status": "connected"})

        # Add reaction
        await communicator.send_to(
            text_data=json.dumps({"type": "add_reaction", "message_id": self.message.id, "emoji": "😊"})
        )

        # Receive session key
        session_key_response = await communicator.receive_from()
        session_key_data = json.loads(session_key_response)
        self.assertEqual(session_key_data["type"], "session_key")
        session_key = session_key_data["session_key"]

        # Receive reaction update
        reaction_response = await communicator.receive_from()
        reaction_data = json.loads(reaction_response)
        self.assertEqual(reaction_data["type"], "reaction_update")
        self.assertIn(f"session_{session_key}", reaction_data["reactions"]["😊"])

        await self.message.arefresh_from_db()
        self.assertIn(f"session_{session_key}", self.message.reactions["😊"])

        # Remove reaction
        await communicator.send_to(
            text_data=json.dumps(
                {"type": "add_reaction", "message_id": self.message.id, "emoji": "😊", "session_key": session_key}
            )
        )

        # Receive session key again (sent for anonymous users)
        await communicator.receive_from()
        # Receive reaction update
        response = await communicator.receive_from()
        response_data = json.loads(response)
        self.assertEqual(response_data["type"], "reaction_update")
        self.assertEqual(response_data["reactions"], {})

        await self.message.arefresh_from_db()
        self.assertEqual(self.message.reactions, {})

        await communicator.disconnect()

    async def test_multiple_reactions(self):
        """Test adding multiple reactions from different users."""
        # Logged-in user
        communicator = WebsocketCommunicator(application, f"/ws/discussion-rooms/chat/{self.room.id}/")
        communicator.scope["user"] = self.user
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Consume connection status message
        response = await communicator.receive_from()
        self.assertEqual(json.loads(response), {"type": "connection_status", "status": "connected"})

        # Add reaction 1
        await communicator.send_to(
            text_data=json.dumps({"type": "add_reaction", "message_id": self.message.id, "emoji": "👍"})
        )
        await communicator.receive_from()

        # Add reaction 2
        await communicator.send_to(
            text_data=json.dumps({"type": "add_reaction", "message_id": self.message.id, "emoji": "❤️"})
        )
        response = await communicator.receive_from()
        response_data = json.loads(response)
        self.assertIn("👍", response_data["reactions"])
        self.assertIn("❤️", response_data["reactions"])

        await communicator.disconnect()

        # Anonymous user
        anon_communicator = WebsocketCommunicator(application, f"/ws/discussion-rooms/chat/{self.room.id}/")
        anon_communicator.scope["user"] = AnonymousUser()
        connected, _ = await anon_communicator.connect()
        self.assertTrue(connected)

        # Consume connection status message
        response = await anon_communicator.receive_from()
        self.assertEqual(json.loads(response), {"type": "connection_status", "status": "connected"})

        # Add reaction from anon user
        await anon_communicator.send_to(
            text_data=json.dumps({"type": "add_reaction", "message_id": self.message.id, "emoji": "😂"})
        )
        session_key_response = await anon_communicator.receive_from()
        session_key = json.loads(session_key_response)["session_key"]
        reaction_response = await anon_communicator.receive_from()
        reaction_data = json.loads(reaction_response)

        self.assertIn("👍", reaction_data["reactions"])
        self.assertIn("❤️", reaction_data["reactions"])
        self.assertIn("😂", reaction_data["reactions"])
        self.assertIn(f"session_{session_key}", reaction_data["reactions"]["😂"])

        await self.message.arefresh_from_db()
        self.assertIn("👍", self.message.reactions)
        self.assertIn("❤️", self.message.reactions)
        self.assertIn("😂", self.message.reactions)
        self.assertIn(f"session_{session_key}", self.message.reactions["😂"])

        await anon_communicator.disconnect()
