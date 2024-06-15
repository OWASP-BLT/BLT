import json

from channels.generic.websocket import AsyncWebsocketConsumer

from notification_app.models import Notification


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope["url_route"]["kwargs"]["room_name"]
        self.room_group_name = "notification_%s" % self.room_name

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        notification_id = data["notification_id"]
        Notification.objects.filter(id=notification_id).delete()

    # Receive message from room group
    async def send_notification(self, event):
        print("===========", event)
        message = event
        # Send message to WebSocket
        await self.send(text_data=json.dumps(message))
