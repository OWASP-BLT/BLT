import logging
from typing import Any, Dict, List, Optional

from django.conf import settings
from google.genai import types

from website.aibot.clients import g_client

logger = logging.getLogger(__name__)


def generate_gemini_response(prompt: str, model: str = settings.GEMINI_GENERATION_MODEL) -> Optional[Dict[str, Any]]:
    """
    Generates a response from the Gemini model for the given prompt.
    Returns structured data including text, model info, and token usage.
    """

    if not prompt or not isinstance(prompt, str):
        raise ValueError(f"Invalid prompt provided: {prompt}. Prompt must be a non-empty string.")

    try:
        response = g_client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                thinking_config=types.ThinkingConfig(thinking_budget=0)  # Disable thinking
            ),
        )

        text = None
        if response and response.candidates:
            candidate = response.candidates[0]
            if candidate.content.parts:
                text = candidate.content.parts[0].text

        if text:
            return {
                "text": text,
                "model": getattr(response, "model_version", model),
                "response_id": getattr(response, "response_id", None),
                "prompt_tokens": getattr(response.usage_metadata, "prompt_token_count", 0),
                "completion_tokens": getattr(response.usage_metadata, "candidates_token_count", 0),
                "total_tokens": getattr(response.usage_metadata, "total_token_count", 0),
            }

        logger.warning(
            "Gemini model returned an empty or non-text response for prompt: '%s'. Response: %s", prompt, response
        )
        return None

    except Exception as e:
        logger.error("Gemini API error for prompt '%s': %s", prompt, e, exc_info=True)
        return None


def generate_embedding(
    text: str, task_type: str, embedding_model: str = settings.GEMINI_EMBEDDING_MODEL
) -> Optional[List[float]]:
    """
    Generates an embedding from the given text using the Gemini model.

    Args:
        text (str): The input text.
        title (str, optional): Title of the content. Defaults to "Untitled".
        embedding_model (str): The Gemini embedding model to use.

    Returns:
        Optional[List[float]]: The embedding vector, or None if an error occurs.
    """
    try:
        response = g_client.models.embed_content(
            model=embedding_model,
            contents=text,
            config=types.EmbedContentConfig(output_dimensionality=settings.QDRANT_VECTOR_SIZE, task_type=task_type),
        )
        [embeddings] = response.embeddings
        return embeddings.values
    except Exception as e:
        logger.error(f"Embedding generation failed for text: {text} - {e}")
        return None
