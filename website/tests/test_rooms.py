import json
import sys
import uuid
from unittest.mock import MagicMock

# Mock daphne to allow tests to run without installing it
sys.modules["daphne"] = MagicMock()
sys.modules["daphne.testing"] = MagicMock()

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

    async def test_anonymous_connection_receives_session_key(self):
        """Test that an anonymous user receives a session key upon connecting."""
        communicator = WebsocketCommunicator(application, f"/ws/discussion-rooms/chat/{self.room.id}/")
        communicator.scope["user"] = AnonymousUser()
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # First message should be the session key
        response = await communicator.receive_from()
        data = json.loads(response)
        self.assertEqual(data["type"], "session_key")
        self.assertTrue("session_key" in data)
        self.assertTrue(len(data["session_key"]) > 16)  # Check it's a UUID

        # Second message should be the connection status
        response = await communicator.receive_from()
        self.assertEqual(json.loads(response), {"type": "connection_status", "status": "connected"})

        await communicator.disconnect()

    async def test_authenticated_user_sends_message(self):
        """Test that a logged-in user can send a message."""
        communicator = WebsocketCommunicator(application, f"/ws/discussion-rooms/chat/{self.room.id}/")
        communicator.scope["user"] = self.user
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.receive_from()  # Connection status

        await communicator.send_to(text_data=json.dumps({"type": "chat_message", "message": "Hello world!"}))

        # Receive message_ack first
        ack_response = await communicator.receive_from()
        self.assertEqual(json.loads(ack_response)["type"], "message_ack")

        # Then receive the broadcasted chat_message
        response = await communicator.receive_from()
        data = json.loads(response)
        self.assertEqual(data["type"], "chat_message")
        self.assertEqual(data["username"], self.user.username)
        self.assertEqual(data["message"], "Hello world!")

        # Check database
        self.assertTrue(await Message.objects.filter(user=self.user, content="Hello world!").aexists())
        await communicator.disconnect()

    async def test_anonymous_user_sends_message(self):
        """Test that an anonymous user can send a message."""
        communicator = WebsocketCommunicator(application, f"/ws/discussion-rooms/chat/{self.room.id}/")
        communicator.scope["user"] = AnonymousUser()
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Get session key
        session_key_data = json.loads(await communicator.receive_from())
        session_key = session_key_data["session_key"]
        await communicator.receive_from()  # Connection status

        await communicator.send_to(text_data=json.dumps({"type": "chat_message", "message": "I am anonymous"}))

        # Receive message_ack first
        ack_response = await communicator.receive_from()
        self.assertEqual(json.loads(ack_response)["type"], "message_ack")

        # Then receive the broadcasted chat_message
        response = await communicator.receive_from()
        data = json.loads(response)
        self.assertEqual(data["type"], "chat_message")
        self.assertEqual(data["username"], f"anon_{session_key}")
        self.assertEqual(data["message"], "I am anonymous")

        # Check database
        msg = await Message.objects.aget(content="I am anonymous")
        self.assertEqual(msg.session_key, session_key)
        self.assertIsNone(msg.user)

        await communicator.disconnect()

    async def test_logged_in_user_add_and_remove_reaction(self):
        """Test that a logged-in user can add and remove a reaction."""
        communicator = WebsocketCommunicator(application, f"/ws/discussion-rooms/chat/{self.room.id}/")
        communicator.scope["user"] = self.user
        connected, _ = await communicator.connect()
        self.assertTrue(connected)
        await communicator.receive_from()  # Connection status

        # Add reaction
        await communicator.send_to(
            text_data=json.dumps({"type": "add_reaction", "message_id": self.message.id, "emoji": "👍"})
        )

        response = await communicator.receive_from()
        response_data = json.loads(response)
        self.assertEqual(response_data["type"], "reaction_update")
        self.assertIn(str(self.user.pk), response_data["reactions"]["👍"])

        # Remove reaction
        await communicator.send_to(
            text_data=json.dumps({"type": "add_reaction", "message_id": self.message.id, "emoji": "👍"})
        )
        response = await communicator.receive_from()
        response_data = json.loads(response)
        self.assertEqual(response_data["reactions"], {})

        await communicator.disconnect()

    async def test_anonymous_user_add_and_remove_reaction(self):
        """Test that an anonymous user can add and remove a reaction."""
        communicator = WebsocketCommunicator(application, f"/ws/discussion-rooms/chat/{self.room.id}/")
        communicator.scope["user"] = AnonymousUser()
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        # Receive session key and connection status
        session_key_response = await communicator.receive_from()
        session_key = json.loads(session_key_response)["session_key"]
        await communicator.receive_from()

        # Add reaction
        await communicator.send_to(
            text_data=json.dumps({"type": "add_reaction", "message_id": self.message.id, "emoji": "😊"})
        )
        reaction_response = await communicator.receive_from()
        reaction_data = json.loads(reaction_response)
        self.assertIn(session_key, reaction_data["reactions"]["😊"])

        # Remove reaction (without sending session_key in payload)
        await communicator.send_to(
            text_data=json.dumps({"type": "add_reaction", "message_id": self.message.id, "emoji": "😊"})
        )
        response = await communicator.receive_from()
        response_data = json.loads(response)
        self.assertEqual(response_data["reactions"], {})

        await communicator.disconnect()

    async def test_message_broadcast_to_multiple_users(self):
        """Test that a message is broadcast to all users in a room."""
        comm1 = WebsocketCommunicator(application, f"/ws/discussion-rooms/chat/{self.room.id}/")
        comm1.scope["user"] = self.user
        await comm1.connect()
        await comm1.receive_from()  # comm1 connection status

        comm2 = WebsocketCommunicator(application, f"/ws/discussion-rooms/chat/{self.room.id}/")
        comm2.scope["user"] = AnonymousUser()
        await comm2.connect()
        await comm2.receive_from()  # comm2 session key
        await comm2.receive_from()  # comm2 connection status

        # User 1 sends a message
        await comm1.send_to(text_data=json.dumps({"type": "chat_message", "message": "Broadcast test"}))

        # User 1 receives their own message and ack
        await comm1.receive_from()
        await comm1.receive_from()

        # User 2 should receive the broadcast
        response = await comm2.receive_from()
        data = json.loads(response)
        self.assertEqual(data["type"], "chat_message")
        self.assertEqual(data["username"], self.user.username)
        self.assertEqual(data["message"], "Broadcast test")

        await comm1.disconnect()
        await comm2.disconnect()

    async def test_user_can_delete_own_message(self):
        """Test a user can delete their own message."""
        communicator = WebsocketCommunicator(application, f"/ws/discussion-rooms/chat/{self.room.id}/")
        communicator.scope["user"] = self.user
        await communicator.connect()
        await communicator.receive_from()

        # Send delete message request
        await communicator.send_to(text_data=json.dumps({"type": "deleteMessage", "messageId": self.message.id}))

        # Check for delete ack broadcast
        response = await communicator.receive_from()
        data = json.loads(response)
        self.assertEqual(data["type"], "delete_ack")
        self.assertEqual(data["message_id"], self.message.id)

        # Verify message is deleted from DB
        self.assertFalse(await Message.objects.filter(pk=self.message.id).aexists())
        await communicator.disconnect()

    async def test_security_client_cannot_set_session_key(self):
        """Test that a client cannot provide their own session key to impersonate another user."""
        communicator = WebsocketCommunicator(application, f"/ws/discussion-rooms/chat/{self.room.id}/")
        communicator.scope["user"] = AnonymousUser()
        await communicator.connect()

        # Server provides a session key
        server_session_key = json.loads(await communicator.receive_from())["session_key"]
        await communicator.receive_from()  # Connection status

        fake_key = str(uuid.uuid4())

        # Client tries to send a message with a fake key in the payload
        await communicator.send_to(
            text_data=json.dumps({"type": "chat_message", "message": "Impersonation attempt", "session_key": fake_key})
        )

        # Check that the broadcast uses the original, server-provided key
        ack_response = await communicator.receive_from()  # Receive message_ack first
        self.assertEqual(json.loads(ack_response)["type"], "message_ack")

        response = await communicator.receive_from()  # Then receive the broadcasted chat_message
        data = json.loads(response)
        self.assertEqual(data["username"], f"anon_{server_session_key}")
        self.assertNotEqual(data["username"], f"anon_{fake_key}")

        # Check database record
        msg = await Message.objects.aget(content="Impersonation attempt")
        self.assertEqual(msg.session_key, server_session_key)
        self.assertNotEqual(msg.session_key, fake_key)

        await communicator.disconnect()
