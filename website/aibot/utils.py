import hashlib
import json
import logging
import os
import re
import subprocess
import tempfile
from uuid import UUID

from website.aibot.models import ChunkType

logger = logging.getLogger(__name__)


def generate_uuid(file: str, start: int, end: int) -> str:
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


def analyze_code_ruff_bandit(chunks: ChunkType):
    """
    Analyze Python code string with Bandit and Ruff,
    return a clean, natural-language report for LLM consumption.
    """
    for chunk in chunks:
        code_string = chunk["chunk"]
        filename = chunk.get("file") or chunk.get("file_path")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmpfile:
            tmpfile.write(code_string)
            temp_file_path = tmpfile.name

        try:
            bandit_result = subprocess.run(
                ["bandit", "-r", temp_file_path, "--format", "json"], capture_output=True, text=True
            )
            try:
                bandit_data = json.loads(bandit_result.stdout)
                bandit_issues = bandit_data.get("results", [])
            except json.JSONDecodeError:
                bandit_issues = []
                logger.warning("Warning: Failed to parse Bandit output. Received: %s", bandit_result)

            ruff_result = subprocess.run(
                ["ruff", "check", temp_file_path, "--output-format", "json"], capture_output=True, text=True
            )
            try:
                ruff_issues = json.loads(ruff_result.stdout)
            except json.JSONDecodeError:
                ruff_issues = []
                logger.warning("Warning: Failed to parse Ruff output. Received: %s", ruff_result)

            report_lines = []
            if bandit_issues or ruff_issues:
                report_lines.append(f"File: `{filename}`\n")

            if bandit_issues:
                report_lines.append("Security Issues (Bandit)")
                for issue in bandit_issues:
                    line = issue.get("line_number", "?")
                    test_name = issue.get("test_name", "Unknown issue").replace("_", " ").title()
                    severity = issue.get("issue_severity", "Unknown").capitalize()
                    snippet = issue.get("code", "").strip() or "N/A"
                    report_lines.append(f"- Line {line}: {test_name} — {severity} severity.")
                    if snippet != "N/A":
                        report_lines.append(f"  - Code: `{snippet}`")
                    report_lines.append("\n")

            if ruff_issues:
                report_lines.append("Code Quality Issues (Ruff)")
                for issue in ruff_issues:
                    line = issue.get("location", {}).get("row", "?")
                    code = issue.get("code", "")
                    message = issue.get("message", "")
                    report_lines.append(f"- Line {line}: {message} (`{code}`)")

            return "\n".join(report_lines)

        finally:
            os.unlink(temp_file_path)
