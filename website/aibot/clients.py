from django.conf import settings
from google import genai
from qdrant_client import QdrantClient

from website.aibot.aibot_env import configure_and_validate_settings

configure_and_validate_settings()
# TODO: Remove settings config call once testing is done

g_client = genai.Client(api_key=settings.GEMINI_API_KEY)

q_client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_HTTP_PORT)
