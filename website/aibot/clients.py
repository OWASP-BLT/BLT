import google.generativeai as genai
from django.conf import settings
from qdrant_client import QdrantClient

genai.configure(api_key=settings.GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-2.0-flash")

q_client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_HTTP_PORT)
