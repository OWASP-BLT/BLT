import logging
import os

import django
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


def configure_settings() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blt.settings")
    django.setup()


def validate_settings() -> None:
    critical_settings = [
        "GITHUB_AIBOT_WEBHOOK_SECRET",
        "GITHUB_AIBOT_APP_NAME",
        "GITHUB_AIBOT_APP_ID",
        "GITHUB_AIBOT_PRIVATE_KEY_B64",
        "GEMINI_API_KEY",
        "GEMINI_GENERATION_MODEL",
        "GEMINI_EMBEDDING_MODEL",
        "QDRANT_HOST",
        "QDRANT_VECTOR_SIZE",
        "QDRANT_HTTP_PORT",
    ]

    missing_settings = []

    for key in critical_settings:
        if not getattr(settings, key, None):
            missing_settings.append(key)
    if missing_settings:
        missing_settings_str = "\n".join(missing_settings)
        raise ImproperlyConfigured(f"Missing critical settings\n{'-'*50}\n{missing_settings_str}\n{'-'*50}")

    errors = []
    try:
        vsize = int(getattr(settings, "QDRANT_VECTOR_SIZE", 0))
        if vsize <= 0:
            errors.append("QDRANT_VECTOR_SIZE must be a positive integer")
    except (TypeError, ValueError):
        errors.append("QDRANT_VECTOR_SIZE must be an integer")
    try:
        port = int(getattr(settings, "QDRANT_HTTP_PORT", 0))
        if port < 1 or port > 65535:
            errors.append("QDRANT_HTTP_PORT must be between 1 and 65535")
    except (TypeError, ValueError):
        errors.append("QDRANT_HTTP_PORT must be an integer")
    if errors:
        raise ImproperlyConfigured("Invalid settings:\n" + "\n".join(errors))


def configure_and_validate_settings() -> None:
    configure_settings()
    validate_settings()
