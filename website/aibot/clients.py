import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from google import genai
from qdrant_client import QdrantClient

from website.aibot.aibot_env import configure_and_validate_settings

logger = logging.getLogger(__name__)


try:
    configure_and_validate_settings()
except ImproperlyConfigured as e:
    logger.error("Couldn't initialize gemini and qdrant clients due to missing settings.")

g_client = genai.Client(api_key=settings.GEMINI_API_KEY)
q_client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_HTTP_PORT)
