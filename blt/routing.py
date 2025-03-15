from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import re_path

from website.consumers import ChatConsumer, DirectChatConsumer, SimilarityConsumer, VideoCallConsumer

websocket_urlpatterns = [
    re_path(r"ws/similarity/$", SimilarityConsumer.as_asgi()),
    re_path(r"ws/discussion-rooms/chat/(?P<room_id>\d+)/$", ChatConsumer.as_asgi()),
    re_path(r"ws/messaging/(?P<thread_id>\d+)/$", DirectChatConsumer.as_asgi()),
    re_path(r"ws/video/(?P<room_name>\w+)/$", VideoCallConsumer.as_asgi()),
]

application = ProtocolTypeRouter(
    {
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)
