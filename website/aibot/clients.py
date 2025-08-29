from django.conf import settings
from google import genai
from qdrant_client import QdrantClient

g_client = genai.Client(api_key=settings.GEMINI_API_KEY)

q_client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_HTTP_PORT)
