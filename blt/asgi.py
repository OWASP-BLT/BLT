# asgi.py

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blt.settings")
django.setup()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path

from website.consumers import ChatConsumer, SimilarityConsumer

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(
            URLRouter(
                [
                    path("ws/similarity/", SimilarityConsumer.as_asgi()),
                    path(
                        "ws/discussion-rooms/chat/<int:room_id>/",
                        ChatConsumer.as_asgi(),
                    ),
                ]
            )
        ),
    }
)
