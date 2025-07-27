import hashlib
import logging
import os
import re
from uuid import UUID

logger = logging.getLogger(__name__)


def _generate_uuid(file: str, start: int, end: int) -> str:
    """
    Generate a deterministic UUID from file path and line numbers.

    Args:
        file (str): File path or name.
        start (int): Start line number.
        end (int): End line number.

    Returns:
        str: A UUID string generated from the input values.
    """
    raw = f"{file}:{start}:{end}"
    hash_str = hashlib.sha256(raw.encode()).hexdigest()[:32]
    return str(UUID(hex=hash_str))


def get_git_root(path: str) -> str:
    """Returns the Git root directory for the given path."""
    if os.path.isfile(path):
        path = os.path.dirname(path)

    prev = None
    while path != prev:
        git_dir = os.path.join(path, ".git")
        if os.path.isdir(git_dir):
            return path
        prev = path
        path = os.path.dirname(path)

    # Final check at root level (e.g., '/' or 'C:\\')
    if os.path.isdir(os.path.join(path, ".git")):
        return path

    raise FileNotFoundError("Git root not found.")


def extract_json_block(text: str) -> str:
    """
    Extract JSON object from a string possibly wrapped in markdown-style backticks.
    """
    if not text:
        raise ValueError("Empty response")

    # Extract JSON inside triple backticks (```json ... ```)
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1)

    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return text

    raise ValueError("No valid JSON found in response")


def sanitize_backslash(name: str) -> str:
    """Replace any character that's not alphanumeric, underscore, or hyphen with '-'"""
    return re.sub(r"[^a-zA-Z0-9_\-]", "-", name)


def approximate_token_count_char(text: str) -> int:
    """Approximates tokens based on character count - 4 chars per token."""
    return int(len(text) / 4)
