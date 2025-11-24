import asyncio
import difflib
import json
import logging
import os
import secrets
import tempfile
import zipfile
from pathlib import Path

import aiohttp
from asgiref.sync import sync_to_async
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils import timezone

from website.models import Message, Room, Thread
from website.utils import (
    compare_model_fields,
    cosine_similarity,
    extract_django_models,
    extract_function_signatures_and_content,
    generate_embedding,
    git_url_to_zip_url,
)

logger = logging.getLogger(__name__)


class SimilarityConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Accept the WebSocket connection
        self.room_group_name = "similarity_check"
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name,
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave the group when the WebSocket is closed
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name,
        )

    async def receive(self, text_data):
        """
        Handles messages received from the WebSocket.
        Expects a JSON object with type1, type2, repo1, and repo2.
        """
        data = json.loads(text_data)

        type1 = data.get("type1")  # 'github' or 'zip'
        type2 = data.get("type2")  # 'github' or 'zip'
        repo1 = data.get("repo1")  # GitHub URL or ZIP file path
        repo2 = data.get("repo2")  # GitHub URL or ZIP file path
        branch1 = data.get("branch1")  # Branch name for the first repository
        branch2 = data.get("branch2")  # Branch name for the second repository

        if not repo1 or not repo2 or not type1 or not type2:
            await self.send(json.dumps({"error": "Both repositories and their types are required."}))
            return

        if type1 not in ["github", "zip"] or type2 not in ["github", "zip"]:
            await self.send(json.dumps({"error": "Invalid type. Must be 'github' or 'zip'."}))
            return

        try:
            temp_dir = tempfile.mkdtemp()

            # Download or extract the repositories

            zip_repo1 = git_url_to_zip_url(repo1, branch1)
            zip_repo2 = git_url_to_zip_url(repo2, branch2)
            repo1_path = await self.download_or_extract(zip_repo1, type1, temp_dir, "repo1")
            repo2_path = await self.download_or_extract(zip_repo2, type2, temp_dir, "repo2")

            # Process similarity analysis
            matching_details = await self.run_similarity_analysis(repo1_path, repo2_path)

            if not matching_details:
                await self.send(
                    json.dumps(
                        {
                            "status": "error",
                            "error": "No matching details found between the repositories.",
                        }
                    )
                )
                await self.close()
                return

            # Send the result back to the client
            await self.send(json.dumps({"status": "success", "matching_details": matching_details}))
            await self.close()

        except Exception as e:
            # Handle unexpected errors and send an error message
            await self.send(
                json.dumps(
                    {
                        "status": "error",
                        "error": "Please check the repositories/branches and try again.",
                    }
                )
            )
            await self.close()

        finally:
            # Cleanup temporary directory
            if os.path.exists(temp_dir):
                for root, dirs, files in os.walk(temp_dir, topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                os.rmdir(temp_dir)

    async def run_similarity_analysis(self, repo1_path, repo2_path):
        """
        Runs the similarity analysis asynchronously.
        """
        try:
            # Use asyncio.to_thread to run the blocking process_similarity_analysis in a separate thread
            var = await asyncio.to_thread(self.process_similarity_analysis, repo1_path, repo2_path)
            return var
        except asyncio.CancelledError:
            raise  # Re-raise the cancellation error to propagate it

    async def download_or_extract(self, source, source_type, temp_dir, repo_name):
        """
        Download or extract the repository based on the type (GitHub or ZIP).
        :param source: GitHub URL or ZIP file path
        :param source_type: "github" or "zip"
        :param temp_dir: Temporary directory for processing
        :param repo_name: Prefix for naming (repo1 or repo2)
        :return: Path to the extracted repository
        """
        dest_path = os.path.join(temp_dir, repo_name)
        if source_type == "github":
            repo_path = await self.download_and_extract_zip(source, temp_dir, repo_name)
            return repo_path

        elif source_type == "zip":
            # Assume `repo_url_or_path` is a direct path to a ZIP file
            repo_path = await self.extract_zip(source, temp_dir, repo_name)
            return repo_path

        return dest_path

    async def download_and_extract_zip(self, zip_url, temp_dir, repo_name):
        """
        Downloads and extracts a ZIP file from a URL.
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(zip_url) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to download ZIP file. Status code: {response.status}")

                    # Extract the ZIP file
                    zip_file_path = Path(temp_dir) / f"{repo_name}.zip"
                    with open(zip_file_path, "wb") as zip_file:
                        zip_data = await response.read()
                        zip_file.write(zip_data)

                    # Extract to a directory
                    extraction_path = Path(temp_dir) / repo_name
                    try:
                        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
                            zip_ref.extractall(extraction_path)
                    except zipfile.BadZipFile as e:
                        raise Exception(f"Failed to extract ZIP file: {e}")

                    return str(extraction_path)
        except Exception as e:
            raise

    async def extract_zip(self, zip_file_path, temp_dir, repo_name):
        """
        Extracts a local ZIP file.

        Args:
            zip_file_path (str): Path to the local ZIP file.
            temp_dir (str): Temporary directory to store files.
            repo_name (str): Repository identifier.

        Returns:
            str: Path to the extracted contents.
        """
        extraction_path = Path(temp_dir) / repo_name
        with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
            zip_ref.extractall(extraction_path)
        return str(extraction_path)

    def process_similarity_analysis(self, repo1_path, repo2_path):
        """
        Process the similarity analysis between two repositories.
        :param repo1_path: Path to the first repository
        :param repo2_path: Path to the second repository
        :return: Similarity score and matching details
        """
        try:
            asyncio.run(self.send(json.dumps({"progress": 0, "status": "progress"})))
        except Exception as e:
            return None
        matching_details = {
            "functions": [],
            "models": [],
        }

        # Extract function signatures and content
        functions1 = extract_function_signatures_and_content(repo1_path)
        functions2 = extract_function_signatures_and_content(repo2_path)
        function_text_embeddings = {}
        try:
            asyncio.run(self.send(json.dumps({"progress": 25, "status": "progress"})))
        except Exception as e:
            return None

        i = 0
        for func in functions1 + functions2:
            function_text = func["full_text"]

            # Generate embeddings for function text
            text_embedding = generate_embedding(function_text)
            if text_embedding is None:
                logger.error(f"Error generating embedding for function text: {function_text}")
                return None  # Terminate process immediately

            if i % 5 == 0:
                # Ping the frontend every 5 iterations
                try:
                    asyncio.run(self.send(json.dumps({"ping": "ping"})))  # Send ping from the worker thread
                except Exception as e:
                    return None  # Stop the analysis if the connection is lost
            i += 1
            function_text_embeddings[function_text] = text_embedding

        # Notify progress after generating embeddings (60% progress)
        try:
            asyncio.run(self.send(json.dumps({"progress": 60, "status": "progress"})))
        except Exception as e:
            return None

        # Compare functions between the two repositories
        for func1 in functions1:
            for func2 in functions2:
                name_similarity = (
                    difflib.SequenceMatcher(None, func1["signature"]["name"], func2["signature"]["name"]).ratio() * 100
                )

                # Signature similarity using difflib
                signature1 = f"{func1['signature']['name']}({', '.join(func1['signature']['args'])})"
                signature2 = f"{func2['signature']['name']}({', '.join(func2['signature']['args'])})"

                signature_similarity = difflib.SequenceMatcher(None, signature1, signature2).ratio() * 100

                # Content similarity using OpenAI embeddings
                fulltext1 = func1["full_text"]
                fulltext2 = func2["full_text"]

                content_similarity_openai = cosine_similarity(
                    function_text_embeddings[fulltext1], function_text_embeddings[fulltext2]
                )

                # Aggregate similarity
                overall_similarity = (
                    (name_similarity * 0.25)  # 25% for name similarity
                    + (signature_similarity * 0.25)  # 25% for signature similarity
                    + (content_similarity_openai * 0.5)  # 50% for content similarity
                )

                matching_details["functions"].append(
                    {
                        "name1": func1["signature"]["name"],
                        "name2": func2["signature"]["name"],
                        "name_similarity": round(name_similarity, 2),
                        "signature_similarity": round(signature_similarity, 2),
                        "content_similarity": round(content_similarity_openai, 2),
                        "similarity": round(overall_similarity, 2),
                    }
                )

        # Notify progress after extracting models (75% progress)
        try:
            asyncio.run(self.send(json.dumps({"progress": 75, "status": "progress"})))
        except Exception as e:
            return None

        # Compare Django models
        models1 = extract_django_models(repo1_path)
        models2 = extract_django_models(repo2_path)
        for model1 in models1:
            for model2 in models2:
                model_similarity = difflib.SequenceMatcher(None, model1["name"], model2["name"]).ratio() * 100

                model_fields_similarity = compare_model_fields(model1, model2)
                matching_details["models"].append(
                    {
                        "name1": model1["name"],
                        "name2": model2["name"],
                        "similarity": round(model_similarity, 2),
                        "field_comparison": model_fields_similarity,
                    }
                )
        # Notify progress after completing all comparisons (100% progress)
        try:
            asyncio.run(self.send(json.dumps({"progress": 100, "status": "progress"})))
        except Exception as e:
            return None

        return matching_details


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.room_id = self.scope["url_route"]["kwargs"]["room_id"]
            self.room_group_name = f"chat_{self.room_id}"
            self.connected = False

            # Verify room exists
            room_exists = await self.check_room_exists()
            if not room_exists:
                await self.close(code=4004)
                return

            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            self.connected = True
            await self.accept()

            # Send connection status
            await self.send(text_data=json.dumps({"type": "connection_status", "status": "connected"}))

        except Exception as e:
            await self.close(code=4000)

    async def disconnect(self, close_code):
        try:
            self.connected = False
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

            # Send disconnect status if possible
            try:
                await self.send(
                    text_data=json.dumps({"type": "connection_status", "status": "disconnected", "code": close_code})
                )
            except:
                pass
        except:
            pass

    @database_sync_to_async
    def check_room_exists(self):
        try:
            return Room.objects.filter(id=self.room_id).exists()
        except:
            return False

    def get_or_create_session_key(self, data):
        """Get existing session key from scope or data, or generate a new one."""
        session_key = (
            self.scope.get("session", {}).get("session_key") or data.get("session_key") or secrets.token_urlsafe(8)
        )

        # Store session key in scope for future use
        if "session" not in self.scope:
            self.scope["session"] = {}
        self.scope["session"]["session_key"] = session_key

        return session_key

    @database_sync_to_async
    def save_message(self, message, username):
        """Saves a message in the database."""
        try:
            room = Room.objects.get(id=self.room_id)
            user = None
            session_key = None

            if username.startswith("anon_"):
                # Safely extract session key from username
                parts = username.split("_", 1)
                if len(parts) > 1:
                    session_key = parts[1]
            else:
                user = User.objects.filter(username=username).first()

            return Message.objects.create(
                room=room, user=user, username=username, content=message, session_key=session_key
            )
        except Exception as e:
            return None

    @database_sync_to_async
    def delete_message(self, message_id, username, room_id):
        """Deletes a message if it exists and belongs to the user in the room."""
        try:
            message_object = Message.objects.filter(id=message_id, username=username, room=room_id).first()

            if message_object:
                rows_deleted, _ = message_object.delete()
                return rows_deleted > 0  # True if deleted, False otherwise
            return False
        except Exception as e:
            return False  # Handle unexpected errors gracefully

    @database_sync_to_async
    def add_reaction(self, message_id, emoji, username):
        """
        Adds or toggles a reaction (emoji) on a message.

        If the user has not yet reacted to the message with the given emoji, their reaction is added.
        If the user has already reacted with the same emoji, their reaction is removed (toggle behavior).
        Multiple emoji reactions per user are supported. Users can only remove their own reactions.

        Args:
            message_id (int): The ID of the message to react to.
            emoji (str): The emoji to add or remove (e.g., "👍", "❤️").
            username (str): The username of the user adding/removing the reaction. For anonymous users,
                this should be in the format "anon_{session_key}".

        Returns:
            dict: The updated reactions dictionary if successful, or None if the operation failed.

        Note:
            - Anonymous users are identified by usernames starting with "anon_" and are stored in reactions
              as "session_{session_key}".
            - The toggle behavior means that if a user has already reacted with the given emoji, their reaction
              will be removed; otherwise, it will be added.
        """
        try:
            message = Message.objects.get(id=message_id)
            reactions = message.reactions or {}

            # Handle anonymous users - extract session key from anon_ prefix
            is_anonymous = username.startswith("anon_")
            if is_anonymous:
                # Safely extract session key from username
                parts = username.split("_", 1)
                if len(parts) > 1:
                    user_id = f"session_{parts[1]}"
                else:
                    # Fallback for malformed anonymous username
                    user_id = username
            else:
                user_id = username

            # Check if user already has this emoji reaction
            if emoji in reactions:
                if user_id in reactions[emoji]:
                    # User can only remove their own reaction
                    reactions[emoji].remove(user_id)
                    if not reactions[emoji]:
                        del reactions[emoji]
                else:
                    # Add new reaction for this emoji
                    reactions[emoji].append(user_id)
            else:
                # Create new emoji reaction list
                reactions[emoji] = [user_id]

            message.reactions = reactions
            message.save()
            return reactions
        except Message.DoesNotExist:
            return None
        except Exception as e:
            return None

    async def receive(self, text_data):
        """Handles incoming WebSocket messages, including sending and deleting chat messages."""

        if not self.connected:
            await self.send(
                text_data=json.dumps(
                    {"type": "error", "code": "not_connected", "message": "Not connected to chat room"}
                )
            )
            return

        try:
            data = json.loads(text_data)
            message_type = data.get("type", "message")

            # Handle reactions
            if message_type == "add_reaction":
                message_id = data.get("message_id")
                emoji = data.get("emoji")

                # Validate emoji input
                if not emoji or not isinstance(emoji, str):
                    await self.send(
                        text_data=json.dumps({"type": "error", "code": "invalid_emoji", "message": "Invalid emoji"})
                    )
                    return

                # Limit emoji length to prevent abuse (emojis are typically 1-4 characters)
                if len(emoji) > 10:
                    await self.send(
                        text_data=json.dumps(
                            {"type": "error", "code": "invalid_emoji", "message": "Emoji too long"}
                        )
                    )
                    return

                if not message_id:
                    await self.send(
                        text_data=json.dumps(
                            {"type": "error", "code": "invalid_reaction", "message": "Message ID required"}
                        )
                    )
                    return

                # Get username or generate anonymous session-based username
                if self.scope["user"].is_authenticated:
                    username = self.scope["user"].username
                else:
                    session_key = self.get_or_create_session_key(data)
                    username = f"anon_{session_key}"

                    # Send the session key back to the client
                    await self.send(
                        text_data=json.dumps(
                            {
                                "type": "session_key",
                                "session_key": session_key,
                                "message": "Store this session key for future reactions",
                            }
                        )
                    )

                reactions = await self.add_reaction(message_id, emoji, username)
                if reactions is not None:
                    # Broadcast reaction update to all clients
                    reaction_data = {"type": "reaction_update", "message_id": message_id, "reactions": reactions}
                    await self.channel_layer.group_send(self.room_group_name, reaction_data)
                else:
                    await self.send(
                        text_data=json.dumps(
                            {"type": "error", "code": "reaction_failed", "message": "Failed to add reaction"}
                        )
                    )

            # Handle new messages
            elif message_type == "message" or message_type == "chat_message":
                message = data.get("message", "").strip()

                # Get proper username for authenticated or anonymous users
                if self.scope["user"].is_authenticated:
                    username = self.scope["user"].username
                else:
                    session_key = self.get_or_create_session_key(data)
                    username = f"anon_{session_key}"

                if not message:
                    await self.send(
                        text_data=json.dumps(
                            {"type": "error", "code": "invalid_message", "message": "Message cannot be empty"}
                        )
                    )
                    return

                if len(message) > 1000:
                    await self.send(
                        text_data=json.dumps(
                            {
                                "type": "error",
                                "code": "message_too_long",
                                "message": "Message too long (max 1000 chars)",
                            }
                        )
                    )
                    return

                saved_message = await self.save_message(message, username)

                if saved_message:
                    # Broadcast message to all clients
                    message_data = {
                        "type": "chat_message",
                        "message": message,
                        "username": username,
                        "message_id": saved_message.id,
                        "timestamp": saved_message.timestamp.isoformat(),
                    }
                    await self.channel_layer.group_send(self.room_group_name, message_data)
                    await self.send(json.dumps({"type": "message_ack", "message_id": saved_message.id}))
                else:
                    await self.send(json.dumps({"type": "error", "code": "save_failed", "message": "Failed to save"}))

            # Handle message deletion
            elif message_type == "deleteMessage":
                message_id = data.get("messageId")
                username = data.get("username", "Anonymous")

                if not message_id:
                    await self.send(
                        json.dumps({"type": "error", "code": "invalid_message_id", "message": "Message ID required"})
                    )
                    return

                # Attempt to delete the message
                message_deleted = await self.delete_message(message_id, username, self.room_id)

                if message_deleted:
                    # Notify all clients to remove the message from their UI
                    delete_notification = {"type": "delete_message_broadcast", "message_id": message_id}
                    await self.channel_layer.group_send(self.room_group_name, delete_notification)
                    await self.send(json.dumps(delete_notification))  # Send acknowledgment to the sender
                else:
                    await self.send(
                        json.dumps({"type": "error", "code": "delete_failed", "message": "Failed to delete"})
                    )

            elif message_type == "ping":
                await self.send(text_data=json.dumps({"type": "pong", "timestamp": timezone.now().isoformat()}))

        except json.JSONDecodeError:
            await self.send(
                text_data=json.dumps({"type": "error", "code": "invalid_format", "message": "Invalid message format"})
            )
        except Exception as e:
            await self.send(
                text_data=json.dumps({"type": "error", "code": "internal_error", "message": "Internal server error"})
            )

    async def chat_message(self, event):
        if not self.connected:
            return

        try:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "chat_message",
                        "message": event["message"],
                        "username": event["username"],
                        "timestamp": event.get("timestamp"),
                        "message_id": event.get("message_id"),
                    }
                )
            )
        except Exception as error:
            # Log the error instead of silently passing
            logger.error(f"Error sending chat message: {str(error)}")

    async def delete_message_broadcast(self, event):
        """Handles broadcasting delete notifications to all users in the room."""

        if not self.connected:
            return

        try:
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "delete_ack",
                        "message_id": event["message_id"],
                    }
                )
            )

        except Exception as e:
            logger.error(f"Error in delete_message_broadcast: {e}")

    async def reaction_update(self, event):
        """Handles broadcasting reaction updates to all users in the room."""
        if not self.connected:
            return

        try:
            await self.send(
                text_data=json.dumps(
                    {"type": "reaction_update", "message_id": event["message_id"], "reactions": event["reactions"]}
                )
            )
        except Exception as error:
            logger.error(f"Error sending reaction update: {str(error)}")


class DirectChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.thread_id = self.scope["url_route"]["kwargs"]["thread_id"]
        self.room_group_name = f"chat_{self.thread_id}"

        # Join the chat room
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Leave the chat room
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        user = self.scope["user"]
        if user.is_authenticated:
            message = await self.save_message(user, data["encrypted_content"])
            message = data["encrypted_content"]
            # Broadcast message to the chat room
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "username": user.username,
                    "encrypted_content": message,
                },
            )

    async def chat_message(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "type": "chat_message",
                    "username": event["username"],
                    "encrypted_content": event["encrypted_content"],
                }
            )
        )

    @sync_to_async
    def save_message(self, user, encrypted_content):
        thread = get_object_or_404(Thread, id=self.thread_id)
        return Message.objects.create(thread=thread, user=user, username=user.username, content=encrypted_content)


class VideoCallConsumer(AsyncWebsocketConsumer):
    rooms = {}  # Class variable to store room states

    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = f"video_{self.room_name}"

        # Check if room exists and has less than 2 participants
        if self.room_name in self.rooms:
            if len(self.rooms[self.room_name]) >= 2:
                await self.close(code=4000)  # Room is full
                return
            self.rooms[self.room_name].append(self.channel_name)
        else:
            self.rooms[self.room_name] = [self.channel_name]

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        # Notify about participant count
        participant_count = len(self.rooms[self.room_name])
        await self.channel_layer.group_send(self.room_group_name, {"type": "room_status", "count": participant_count})

    async def disconnect(self, close_code):
        # Remove from room
        if self.room_name in self.rooms:
            self.rooms[self.room_name].remove(self.channel_name)
            if not self.rooms[self.room_name]:
                del self.rooms[self.room_name]
            else:
                # Notify remaining participant
                await self.channel_layer.group_send(self.room_group_name, {"type": "peer_disconnected"})

        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            # Forward message to all peers in the room except sender
            if message_type in ["offer", "answer", "ice-candidate"]:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {"type": "video_message", "sender_channel_name": self.channel_name, "data": data},
                )
            elif message_type == "join":
                # Notify others in the room
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        "type": "video_message",
                        "sender_channel_name": self.channel_name,
                        "data": {"type": "join", "room": data.get("room")},
                    },
                )
            elif message_type == "end_call":
                # Notify others that call is ending
                await self.channel_layer.group_send(self.room_group_name, {"type": "call_ended"})

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"error": "Invalid JSON format"}))
        except Exception as e:
            await self.send(text_data=json.dumps({"error": "Internal server error"}))

    async def video_message(self, event):
        # Don't send the message back to the sender
        if self.channel_name != event.get("sender_channel_name"):
            # Send message to WebSocket
            await self.send(text_data=json.dumps(event["data"]))

    async def room_status(self, event):
        # Send room status to client
        await self.send(text_data=json.dumps({"type": "room_status", "count": event["count"]}))

    async def peer_disconnected(self, event):
        # Notify client that peer disconnected
        await self.send(text_data=json.dumps({"type": "peer_disconnected"}))

    async def call_ended(self, event):
        # Notify client that call has ended
        await self.send(text_data=json.dumps({"type": "call_ended"}))
