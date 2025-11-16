import asyncio
import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.utils import timezone

from .models import GitHubEvent, Leaderboard, MonitoredEntity, UserChannel

logger = logging.getLogger(__name__)


class SportscasterConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time sportscaster updates"""

    async def connect(self):
        """Handle WebSocket connection"""
        self.room_group_name = "sportscaster_live"
        self.channel_id = self.scope["url_route"]["kwargs"].get("channel_id", None)

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        # Send connection confirmation
        await self.send(
            text_data=json.dumps(
                {"type": "connection_status", "status": "connected", "timestamp": timezone.now().isoformat()}
            )
        )

        # Start sending updates
        asyncio.create_task(self.send_periodic_updates())

    async def disconnect(self, close_code):
        """Handle WebSocket disconnect"""
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        try:
            data = json.loads(text_data)
            message_type = data.get("type")

            if message_type == "ping":
                await self.send(text_data=json.dumps({"type": "pong", "timestamp": timezone.now().isoformat()}))

            elif message_type == "get_leaderboard":
                leaderboard = await self.get_leaderboard_data()
                await self.send(text_data=json.dumps({"type": "leaderboard", "data": leaderboard}))

            elif message_type == "get_recent_events":
                events = await self.get_recent_events()
                await self.send(text_data=json.dumps({"type": "events", "data": events}))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"type": "error", "message": "Invalid JSON"}))
        except Exception as e:
            logger.error(f"Error in receive: {e}")
            await self.send(text_data=json.dumps({"type": "error", "message": "Internal server error"}))

    async def send_periodic_updates(self):
        """Send periodic updates to the client"""
        try:
            while True:
                # Get recent events
                events = await self.get_recent_events(limit=5)

                if events:
                    await self.send(text_data=json.dumps({"type": "live_update", "events": events}))

                # Wait before next update
                await asyncio.sleep(10)  # Update every 10 seconds

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Error in send_periodic_updates: {e}")

    @database_sync_to_async
    def get_leaderboard_data(self):
        """Get current leaderboard data"""
        try:
            entries = Leaderboard.objects.select_related("monitored_entity").order_by("rank")[:10]

            return [
                {
                    "rank": entry.rank,
                    "name": entry.monitored_entity.name,
                    "metric": entry.metric_type,
                    "value": entry.current_value,
                    "previous_value": entry.previous_value,
                    "change": entry.current_value - entry.previous_value,
                }
                for entry in entries
            ]
        except Exception as e:
            logger.error(f"Error getting leaderboard data: {e}")
            return []

    @database_sync_to_async
    def get_recent_events(self, limit=10):
        """Get recent GitHub events with commentary"""
        try:
            if self.channel_id:
                # Get events for specific channel
                try:
                    channel = UserChannel.objects.get(id=self.channel_id)
                    entity_ids = channel.monitored_entities.values_list("id", flat=True)
                    events = GitHubEvent.objects.filter(monitored_entity_id__in=entity_ids).select_related(
                        "monitored_entity"
                    )[:limit]
                except UserChannel.DoesNotExist:
                    events = []
            else:
                # Get all recent events
                events = GitHubEvent.objects.select_related("monitored_entity").order_by("-timestamp")[:limit]

            return [
                {
                    "id": event.id,
                    "type": event.event_type,
                    "repository": event.monitored_entity.name,
                    "commentary": event.commentary_text or "No commentary available",
                    "timestamp": event.timestamp.isoformat(),
                    "data": event.event_data,
                }
                for event in events
            ]
        except Exception as e:
            logger.error(f"Error getting recent events: {e}")
            return []

    async def broadcast_event(self, event):
        """Broadcast a new event to all connected clients"""
        await self.send(text_data=json.dumps({"type": "new_event", "event": event["event"]}))

    async def broadcast_leaderboard_update(self, event):
        """Broadcast leaderboard update to all connected clients"""
        await self.send(text_data=json.dumps({"type": "leaderboard_update", "data": event["data"]}))
