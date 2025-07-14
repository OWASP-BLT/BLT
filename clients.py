import os

import google.generativeai as genai
from qdrant_client import QdrantClient

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

qdrant_client = QdrantClient(host=os.environ.get("QDRANT_HOST"), port=os.environ.get("QDRANT_HTTP_PORT"))
genai.configure(api_key=GEMINI_API_KEY)

gemini_model = genai.GenerativeModel("gemini-2.0-flash")
