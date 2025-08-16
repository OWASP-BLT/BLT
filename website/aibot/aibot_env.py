import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

import django
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)


BASE_PATH = Path("website/aibot")
SCHEMA_PATH = BASE_PATH / "schemas"
PROMPT_PATH = BASE_PATH / "prompts"


def configure_settings() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blt.settings")
    django.setup()


def validate_settings() -> None:
    critical_settings = [
        "GITHUB_AIBOT_WEBHOOK_URL",
        "GITHUB_AIBOT_WEBHOOK_ID",
        "GITHUB_AIBOT_WEBHOOK_SECRET",
        "GITHUB_AIBOT_USERNAME",
        "GITHUB_URL",
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
        logger.critical(f"Missing critical settings: {', '.join(missing_settings)}")
        raise ImproperlyConfigured(f"Missing critical settings: {', '.join(missing_settings)}")


def configure_and_validate_settings() -> None:
    configure_settings()
    validate_settings()


def load_validation_schemas() -> Dict[str, Any]:
    schemas = {}
    schema_files = {
        "COMMENT_SCHEMA": "comment_schema.json",
        "ISSUE_SCHEMA": "issue_schema.json",
        "PR_SCHEMA": "pr_schema.json",
    }

    for schema_name, file_name in schema_files.items():
        file_path = SCHEMA_PATH / file_name

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                schemas[schema_name] = json.load(f)
        except FileNotFoundError:
            logger.critical("CRITICAL ERROR: Schema file not found: %s. Application cannot start.", file_path)
            raise
        except json.JSONDecodeError as e:
            logger.critical(
                "CRITICAL ERROR: Failed to parse JSON for schema %s from %s: %s. Application cannot start.",
                schema_name,
                file_path,
                e,
            )
            raise
        except Exception as e:
            logger.critical(
                "CRITICAL ERROR: An unexpected error occurred while loading schema %s from %s: %s. Application cannot start.",
                schema_name,
                file_path,
                e,
            )
            raise
    return schemas


def load_prompts() -> Dict[str, str]:
    prompts = {}
    prompt_files = {
        "PR_REVIEWER_PROMPT": "pr_reviewer.txt",
        "SEMANTIC_QUERY_GENERATOR_PROMPT": "semantic_query_generator.txt",
    }

    for prompt_name, file_name in prompt_files.items():
        file_path = PROMPT_PATH / file_name
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                prompts[prompt_name] = f.read().strip()
        except FileNotFoundError:
            logger.critical("CRITICAL ERROR: Prompt file not found: %s. Application cannot start.", file_path)
            raise
        except Exception as e:
            logger.critical(
                "CRITICAL ERROR: An unexpected error occurred while loading prompt %s from %s: %s. Application cannot start.",
                prompt_name,
                file_path,
                e,
            )
            raise
    return prompts
