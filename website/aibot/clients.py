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
    logger.error("Couldn't initialize Gemini/Qdrant clients due to missing settings: %s", e, exc_info=True)
    g_client = None
    q_client = None
else:
    g_client = genai.Client(api_key=settings.GEMINI_API_KEY)
    q_client = QdrantClient(
        host=getattr(settings, "QDRANT_HOST", "qdrant"),
        port=int(getattr(settings, "QDRANT_HTTP_PORT", 6333)),
        timeout=10.0,
    )
