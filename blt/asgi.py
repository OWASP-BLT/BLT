# asgi.py

import os
import tracemalloc

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blt.settings")
django.setup()

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application
from django.urls import path

tracemalloc.start()

from website import consumers  # You will define a consumer for handling WebSockets

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AuthMiddlewareStack(
            URLRouter(
                [
                    path("ws/similarity/", consumers.SimilarityConsumer.as_asgi()),  # WebSocket URL
                ]
            )
        ),
    }
)
