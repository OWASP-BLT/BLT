import hashlib
import hmac
import json
import logging
import os
import re
import subprocess
import tempfile
from typing import Any, Dict, Tuple
from uuid import UUID

from django.http import HttpRequest
from unidiff import PatchedFile, PatchSet

from website.aibot.types import ChunkType

logger = logging.getLogger(__name__)


def generate_chunk_uuid(chunk: ChunkType) -> str:
    """
    Generate a deterministic UUID from file path and line numbers.

    Args:
        file (str): File path or name.
        start (int): Start line number.
        end (int): End line number.

    Returns:
        str: A UUID string generated from the input values.
    """
    raw = f"{chunk['file_path']}:{chunk['start_line']}:{chunk['end_line']}:{chunk['part_index']}:{chunk['part_total']}"
    hash_str = hashlib.sha256(raw.encode()).hexdigest()[:32]
    return str(UUID(hex=hash_str))


def validate_github_request(request: HttpRequest) -> Tuple[bool, str]:
    if not request.body:
        return False, "Empty request body received."

    event_type = request.headers.get("X-GitHub-Event", None)
    if not event_type:
        return False, "Missing X-GitHub-Event header."

    return True, ""


def sign_payload(secret: str, payload_body: bytes) -> str:
    if not secret:
        logger.error("Webhook secret is required to sign payload")
        return None
    if not isinstance(payload_body, bytes):
        logger.error("payload_body must be bytes")
        return None

    mac = hmac.new(secret.encode("utf-8"), payload_body, hashlib.sha256)
    hex_digest = mac.hexdigest()
    return f"sha256={hex_digest}"


def verify_github_signature(secret: str, payload_body: bytes, signature_header: str) -> Tuple[bool, str]:
    if not signature_header or not signature_header.startswith("sha256="):
        return False, "Missing/invalid signature"

    if not secret:
        return False, "Webhook secret not configured; cannot verify signature."

    try:
        received_signature = signature_header.split("=", 1)[1]
    except IndexError:
        return False, "Missing/invalid signature"

    mac = hmac.new(secret.encode(), payload_body, hashlib.sha256)
    expected_signature = mac.hexdigest()

    matched = hmac.compare_digest(expected_signature, received_signature)
    if not matched:
        return False, "Missing/invalid signature"

    return True, ""


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


def parse_json(body: str):
    try:
        payload: Dict[str, Any] = json.loads(body)
        return payload
    except json.JSONDecodeError:
        return None


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


def format_chunks_to_string(chunks: ChunkType) -> str:
    formatted_snippets = []
    for snippet in chunks:
        file_path = snippet.get("file_path", "Unknown")
        content = snippet.get("content", "")

        start = snippet.get("start_line", "?")
        end = snippet.get("end_line", "?")

        formatted_snippet = f"File: {file_path}\n" f"Lines: {start}–{end}\n" f"```python\n{content}\n```"
        formatted_snippets.append(formatted_snippet)

    joined_snippets = "\n\n".join(formatted_snippets)
    return joined_snippets


def sanitize_name(name: str) -> str:
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


def process_diff(diff_text: str) -> tuple[str, PatchSet]:
    skip_files = {"package-lock.json", ".yarn.lock"}
    skip_text_extensions = {
        ".lock",
        ".min.js",
        ".map",
        ".pyc",
        ".log",
        ".db",
        ".coverage",
        ".egg-info",
    }
    binary_extensions = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".pdf", ".zip", ".tar", ".gz"}

    processed_diff = []
    binary_changes = []

    def is_skippable_text(file: PatchedFile) -> bool:
        return file.path in skip_files or file.path.endswith(tuple(skip_text_extensions))

    def is_binary_by_extension(file: PatchedFile) -> bool:
        return file.path.endswith(tuple(binary_extensions))

    patch = PatchSet.from_string(diff_text)

    for file in patch:
        if is_skippable_text(file):
            continue

        if file.is_binary_file or is_binary_by_extension(file):
            if file.is_added_file:
                binary_changes.append(f"Binary Added: {file.path}")
            elif file.is_removed_file:
                binary_changes.append(f"Binary Removed: {file.path}")
            elif file.is_rename:
                binary_changes.append(f"Binary Renamed: {file.source_file[2:]} → {file.target_file[2:]}")
            continue

        if file.is_added_file:
            diff_section = f"New: {file.path}\n"
            added_content = [line.value.rstrip("\n") for hunk in file for line in hunk if line.is_added]
            diff_section += "\n".join(added_content) + "\n"
            processed_diff.append(diff_section)

        elif file.is_removed_file:
            diff_section = f"Removed: {file.path}\n"
            removed_content = [line.value.rstrip("\n") for hunk in file for line in hunk if line.is_removed]
            diff_section += "\n".join(removed_content) + "\n"
            processed_diff.append(diff_section)

        elif file.is_rename:
            hunk_output = [str(hunk).rstrip("\n") for hunk in file]
            if hunk_output:
                diff_section = f"Renamed and Modified: {file.source_file[2:]} → {file.target_file[2:]}\n"
                diff_section += "\n".join(hunk_output) + "\n"
            else:
                diff_section = f"Renamed: {file.source_file[2:]} → {file.target_file[2:]}\n\n"
            processed_diff.append(diff_section)

        elif file.is_modified_file:
            diff_section = f"Modified: {file.path}\n"
            hunk_contents = [str(hunk).rstrip("\n") for hunk in file]
            diff_section += "\n".join(hunk_contents) + "\n"
            processed_diff.append(diff_section)

    final_output = "\n".join(binary_changes + processed_diff)
    return final_output, patch


def pr_analysis_marker() -> str:
    return "<!-- AIBOT PR Analysis Marker: v1 -->"


def issue_analysis_marker() -> str:
    return "<!-- AIBOT Issue Analysis Marker: v1 -->"
