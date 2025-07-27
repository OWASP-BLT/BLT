"""This module handles the GitHub AI Bot webhook events and interactions.
It processes pull requests, issues, and comments, and interacts with the
Gemini AI API to generate responses and post them on github.
"""

import hashlib
import hmac
import json
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from jsonschema import ValidationError, validate
from unidiff import PatchedFile, PatchSet

from website.aibot.aibot_env import configure_settings, load_prompts, load_validation_schemas, validate_settings
from website.aibot.models import PullRequest
from website.aibot.network import fetch_pr_diff, generate_embedding, generate_gemini_response
from website.aibot.qdrant_utils import create_temp_pr_collection
from website.aibot.utils import ChunkType, extract_json_block

configure_settings()
validate_settings()

logger = logging.getLogger(__name__)

SCHEMAS = load_validation_schemas()
PROMPTS = load_prompts()


def get_aibot_pr_analysis_comment_marker() -> str:
    """
    Returns the marker used in PR analysis comments to identify them as AI Bot generated.
    This is used to differentiate AI Bot comments from user comments.
    """
    return f"**PR Analysis by {settings.GITHUB_AIBOT_USERNAME}**"


def get_aibot_issue_analysis_comment_marker() -> str:
    """
    Returns the marker used in issue analysis comments to identify them as AI Bot generated.
    This is used to differentiate AI Bot comments from user comments.
    """
    return f"**Issue Analysis by {settings.GITHUB_AIBOT_USERNAME}**"


@require_GET
def aibot_webhook_is_healthy(request: HttpRequest) -> JsonResponse:
    """
    Full health check that ensures:
    1. Django server is up
    2. GitHub webhook endpoint is reachable
    3. Webhook delivery actually works by sending a test payload

    Returns:
        JsonResponse with basic status information
    """

    github_token = settings.GITHUB_AIBOT_TOKEN
    webhook_id = settings.GITHUB_AIBOT_WEBHOOK_ID
    repo_api_url = settings.GITHUB_API_URL
    webhook_url = settings.GITHUB_AIBOT_WEBHOOK_URL

    try:
        ping_url = f"{repo_api_url}/hooks/{webhook_id}/pings"
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        logger.info("Attempting to ping GitHub webhook at %s", ping_url)
        ping_response = requests.post(ping_url, headers=headers, timeout=5)

        if ping_response.status_code != 204:
            logger.error(
                "Webhook ping failed. Status: %s, Response: %s",
                ping_response.status_code,
                ping_response.text,
            )
            return JsonResponse(
                {"health": "0", "status": "Webhook ping failed", "message": "Could not verify webhook connectivity"},
                status=500,
            )

        test_payload = {"test": "webhook_health_check"}
        test_headers = {"X-GitHub-Event": "ping", "Content-Type": "application/json"}
        logger.info("Testing webhook delivery to %s", webhook_url)
        delivery_response = requests.post(webhook_url, json=test_payload, headers=test_headers, timeout=5)

        if delivery_response.status_code != 200:
            logger.error(
                "Webhook delivery failed. Status: %s, Response: %s",
                delivery_response.status_code,
                delivery_response.text,
            )
            return JsonResponse(
                {"health": "0", "status": "Webhook delivery failed", "message": "Could not verify webhook delivery"},
                status=500,
            )
        logger.info("Webhook health check successful. Response from delivery: %s", delivery_response.json())
        return JsonResponse(
            {
                "health": "1",
                "status": "Webhook is reachable and delivery works",
                "repo": settings.GITHUB_URL,
            }
        )
    except requests.RequestException as e:
        logger.error("Request error during webhook health check: %s", str(e), exc_info=True)
        return JsonResponse(
            {
                "health": "2",
                "status": "Error contacting GitHub API or webhook endpoint",
                "message": "Network communication error",
            },
            status=500,
        )
    except ValidationError as ve:
        logger.error("Validation error during webhook health check: %s", str(ve), exc_info=True)
        return JsonResponse(
            {"health": "2", "status": "Validation error", "message": "Error during request validation"},
            status=400,
        )
    except Exception as e:
        logger.error("Unexpected error during webhook health check: %s", str(e), exc_info=True)
        return JsonResponse(
            {"health": "2", "status": "Unexpected error during health check", "message": "Internal server error"},
            status=500,
        )


@csrf_exempt
def main_github_aibot_webhook_dispatcher(request: HttpRequest) -> JsonResponse:
    """
    Main entry point for handling GitHub webhook events.

    This function routes different GitHub webhook events to their respective handlers
    based on the event type and action. Supported events include:
    - Pull Request events (opened, synchronize)
    - Issue comments (bot mentions in PRs or issues)
    - Issue events (opened, mentioned)

    Args:
        request: The incoming HTTP request from GitHub webhook

    Returns:
        JsonResponse: A response indicating the webhook was received successfully,
                      or an error response if the request is in.

    Raises:
        Status 400: If the request method is not POST, request body is empty or JSON is invalid
        Status 403: If the webhook signature verification fails
    """
    if request.method != "POST":
        logger.warning("Invalid request method: %s. Only POST requests are accepted.", request.method)
        return JsonResponse({"error": "Invalid method: Only POST requests are accepted"}, status=400)

    if not request.body:
        logger.warning("Request body is empty.")
        return JsonResponse({"error": "Empty request body received."}, status=400)

    try:
        payload: Dict[str, Any] = json.loads(request.body)
    except json.JSONDecodeError:
        logger.error("Invalid JSON payload received")
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    event_type = request.headers.get("X-GitHub-Event", None)
    if not event_type:
        logger.warning("Missing X-GitHub-Event header.")
        return JsonResponse({"error": "Missing X-GitHub-Event header."}, status=400)

    logger.info("Webhook received - Event: %s, Action: %s", event_type, payload.get("action", "unknown"))
    if event_type == "ping":
        zen = payload.get("zen", "No zen message received.")
        logger.info("Webhook ping received: %s", zen)
        return JsonResponse({"status": "pong", "zen": zen}, status=200)

    signature_header = request.headers.get("X-Hub-Signature-256", None)
    if not signature_header:
        logger.warning("Missing signature header in the request.")
        return JsonResponse({"error": "Missing webhook signature header."}, status=403)

    webhook_secret = settings.GITHUB_AIBOT_WEBHOOK_SECRET
    if not verify_github_signature(webhook_secret, request.body, signature_header):
        logger.warning("Invalid webhook signature received for the Github AIbot webhook.")
        return JsonResponse({"error": "Invalid webhook signature."}, status=403)

    try:
        if event_type == "pull_request":
            logger.info("Processing pull request event")
            handle_pull_request_event(payload)
            return JsonResponse({"status": "Pull request event processed"}, status=200)

        if event_type == "issue_comment":
            logger.info("Processing issue comment event")
            handle_comment_event(payload)
            return JsonResponse({"status": "Comment event processed"}, status=200)

        if event_type == "issues":
            logger.info("Processing issue event")
            handle_issue_event(payload)
            return JsonResponse({"status": "Issue event processed"}, status=200)

        logger.info("Ignoring unsupported event type: %s", event_type)
        return JsonResponse({"status": "Unsupported event type - ignored"})
    except Exception as e:
        logger.error("Unexpected error occurred while processing the webhook request: %s", str(e), exc_info=True)
        return JsonResponse({"error": "Unexpected error occurred while processing the webhook request"}, status=500)


def handle_pull_request_event(payload: Dict[str, Any]) -> JsonResponse:
    """Validate and handle pull request related events (opened, synchronize, closed)."""
    validate_payload_schema(payload, SCHEMAS["PR_SCHEMA"])

    pr_instance = PullRequest(payload)
    action = pr_instance.action

    if action == "opened" or "reopened":  # Reopened for dev purposes
        logger.info("New PR %s: #%s - %s", action, pr_instance.number, pr_instance.title)
        aibot_handle_new_pr_opened(pr_instance)
    elif action == "synchronize":
        logger.info("PR updated: #%s - New commits pushed", pr_instance.number)
        aibot_handle_pr_update(pr_instance)
    elif action == "closed":
        logger.debug("Pr Closed. If no further activity in 3 days, it will deleted from db.")
    return JsonResponse({"status": "PR event processed"})


def handle_comment_event(payload: Dict[str, Any]) -> None:
    """
    Validate and handle comments on PRs/issues where the bot might be mentioned.
    Ignores comments made by the bot itself (present in the validation schema).
    """
    validate_payload_schema(payload, SCHEMAS["COMMENT_SCHEMA"])

    comment = payload.get("comment", {})
    comment_body = comment.get("body", "").lower()

    logger.info(
        "Processing comment event:\n- Comment ID: %s\n- Body: %s\n- User: %s",
        comment.get("id"),
        comment_body[:50],
        comment.get("user", {}).get("login", "unknown"),
    )

    if comment.get("user", {}).get("login") == settings.GITHUB_AIBOT_USERNAME:
        logger.info("Ignoring comment made by the AI Bot itself.")
        return

    if f"@{settings.GITHUB_AIBOT_USERNAME}" in comment_body:
        issue = payload.get("issue", {})
        if "pull_request" in issue:
            logger.info("Bot mentioned in PR comment - analyzing...")
            aibot_handle_pr_comment(payload)
        else:
            logger.info("Bot mentioned in issue comment - analyzing...")
            aibot_handle_issue_comment(payload)
    else:
        logger.info("Comment does not mention the bot. Ignoring.")


def handle_issue_event(payload: Dict[str, Any]) -> JsonResponse:
    """Handle issue related events (opened, edited)."""
    validate_payload_schema(payload, SCHEMAS["ISSUE_SCHEMA"])

    action = payload.get("action")
    issue_data = payload.get("issue", {})
    if action == "opened":
        logger.info("New issue opened: #%s - %s", issue_data.get("number"), issue_data.get("title"))
        aibot_handle_new_issue(payload)
    elif action == "edited":
        logger.info("Issue edited: #%s - %s", issue_data.get("number"), issue_data.get("title"))
        aibot_handle_issue_edited(payload)
    return JsonResponse({"status": "Issue event processed"})


def aibot_handle_new_pr_opened(pr_instance: PullRequest) -> None:
    """Handles the logic when a new PR is opened."""

    pr_diff = fetch_pr_diff(pr_instance.diff_url)

    processed_diff, patch = process_diff(pr_diff)
    diff_query = get_diff_query(processed_diff)
    cleaned_json = extract_json_block(diff_query)
    diff_query_json = json.loads(cleaned_json)

    q = diff_query_json.get("query")
    key_terms = diff_query_json.get("key_terms")
    k = diff_query_json.get("k")

    combined_query = q + key_terms
    vector_query = generate_embedding(combined_query)

    if not vector_query:
        logger.warning("Embedding generation failed for query: %s", combined_query)
    elif not pr_instance.raw_url_map:
        logger.warning("Missing raw URL map for PR instance: %s", pr_instance)
    else:
        temp_collection = create_temp_pr_collection(pr_instance, patch)
        logger.info("Temporary collection created: %s", temp_collection)

    rename_mappings = {}
    for file in patch:
        rename_mappings[file.source_file] = file.target_file

    # TODO manage extraction of source repo or store it
    source_collection = "repo_embeddings"

    similar_chunks = get_similar_merged_chunks(source_collection, temp_collection, vector_query, k)

    analysis_output = get_static_analysis_output(similar_chunks)

    prompt = None
    ai_response = _generate_response(prompt)
    if not ai_response:
        logger.error("Failed to generate AI response for new PR.")
        return

    logger.info("Generated AI response for new PR: %s", ai_response)

    ai_response = f"{get_aibot_pr_analysis_comment_marker()}\n{ai_response}"

    response = None
    # response = post_or_patch_github_comment(pr_number, ai_response)
    if response and response.status_code == 201:
        logger.info("AI Bot response posted successfully: %s", ai_response)
    else:
        logger.error("Failed to post AI Bot response. Response: %s", getattr(response, "text", "No response"))


def get_static_analysis_output(chunks: List[ChunkType]) -> json:
    return


def aibot_handle_pr_update(payload: Dict[str, Any]) -> None:
    """This function handles the logic when a PR is updated with new commits."""
    logger.info("Handling PR update.")
    pr = payload.get("pull_request", {})
    pr_number = pr.get("number")
    pr_title = pr.get("title", "No title")
    head_ref = pr["head"]["ref"]

    context = f"PR Title: {pr_title}\n"

    pr_diff = fetch_pr_diff(pr_number)
    if pr_diff:
        cleaned_diff = process_diff(pr_diff, head_ref)
        context += f"Changes in Update:\n{cleaned_diff}...\n"
    else:
        context += "Unable to fetch changes.\n"

    ai_response = _generate_response(context)
    if not ai_response:
        logger.error("Failed to generate AI response for PR update.")
        return

    logger.info("Generated AI response for PR update: %s", ai_response)

    ai_response = f"{get_aibot_pr_analysis_comment_marker()}\n{ai_response}"

    existing_comment = find_bot_comment(pr_number, get_aibot_pr_analysis_comment_marker())
    comment_id = existing_comment.get("id") if existing_comment else None

    if not comment_id:
        logger.info("No existing bot comment found. Posting a new PR analysis comment.")

    response = post_or_patch_github_comment(pr_number, ai_response, comment_id)
    if response and response.status_code in (200, 201):
        logger.info("AI Bot response posted successfully.")
    else:
        logger.error("Failed to post AI Bot response. Response: %s", getattr(response, "text", "No response"))


def aibot_handle_pr_comment(payload: Dict[str, Any]) -> None:
    """Handle PR comments where the bot is mentioned."""
    pr_number = payload.get("issue", {}).get("number")
    comment_body = payload.get("comment", {}).get("body", "")
    commenter = payload.get("comment", {}).get("user", {}).get("login")

    logger.info(
        "AI Bot processing PR comment:\n- PR #%s\n- Comment by: %s\n- Content: %s...",
        pr_number,
        commenter,
        comment_body[:50],
    )

    ai_response = f"Hi @{commenter}, thanks for tagging me! This is a sample response to your PR comment."
    response = post_or_patch_github_comment(pr_number, ai_response)

    if response and response.status_code == 201:
        logger.info("AI Bot response posted successfully to PR comment.")
    else:
        logger.error(
            "Failed to post AI Bot response to PR comment. Response: %s", getattr(response, "text", "No response")
        )


def aibot_handle_issue_comment(payload: Dict[str, Any]) -> None:
    """Handle issue comments where the bot is mentioned."""
    issue_number = payload.get("issue", {}).get("number")
    comment_body = payload.get("comment", {}).get("body", "")
    commenter = payload.get("comment", {}).get("user", {}).get("login")

    logger.info(
        "AI Bot processing issue comment:\n- Issue #%s\n- Comment by: %s\n- Content: %s...",
        issue_number,
        commenter,
        comment_body[:50],
    )
    prompt = f"""Context:
    - This is a comment on GitHub issue #{issue_number}
    - The commenter is: @{commenter}
    - Their message was: "{comment_body}
    Generate a response for this
    """
    ai_response = _generate_response(prompt)
    response = post_or_patch_github_comment(issue_number, ai_response)

    if response and response.status_code == 201:
        logger.info("AI Bot response posted successfully to issue comment.")
    else:
        logger.error(
            "Failed to post AI Bot response to issue comment. Response: %s", getattr(response, "text", "No response")
        )


def aibot_handle_new_issue(payload: Dict[str, Any]) -> None:
    """
    Handle newly opened GitHub issues.
    Generates a contextual AI response using Gemini.
    """
    issue_number = payload.get("issue", {}).get("number")
    issue_title = payload.get("issue", {}).get("title", "No title")
    issue_body = payload.get("issue", {}).get("body", "No body")

    logger.info(
        "AI Bot processing new issue:\n- Issue #%s\n- Title: %s\n- Content: %s...",
        issue_number,
        issue_title,
        issue_body[:100],
    )

    prompt = f"""
        You are an AI assistant responding to a newly opened GitHub issue.

        Issue Title: {issue_title}
        Issue Description: {issue_body}

        Your task:
        - Briefly acknowledge the issue
        - Summarize what the issue seems to be about
        - Offer help or ask clarifying questions if needed
        - Keep it friendly and professional

        Generate a short, helpful response:
        """

    ai_response = _generate_response(prompt)

    if not ai_response:
        logger.error("Failed to generate AI response for new issue.")
        return

    logger.info("Generated AI response for new issue: %s", ai_response[:150] + "...")

    full_ai_response = f"{get_aibot_issue_analysis_comment_marker()}\n{ai_response}"
    response = post_or_patch_github_comment(issue_number, full_ai_response)

    if response and response.status_code == 201:
        logger.info("AI Bot response posted successfully to new issue #%s.", issue_number)
    else:
        logger.error(
            "Failed to post AI Bot response to new issue #%s. Response: %s",
            issue_number,
            getattr(response, "text", "No response"),
        )


def generate_diff_query(processed_diff: str) -> List[float]:
    template = PROMPTS["SEMANTIC_QUERY_GENERATOR_PROMPT"]
    prompt = template.replace("<DIFF>", processed_diff)
    response = generate_gemini_response(prompt)
    return response


def aibot_handle_issue_edited(payload: Dict[str, Any]) -> None:
    """
    Handle edited GitHub issues by analyzing the updated content and responding accordingly.

    This function:
    - Extracts the issue number, title, and body from the webhook payload.
    - Checks if the AI Bot has already commented on this issue.
    - If a comment exists, updates it with a new analysis.
    - Otherwise, posts a new comment.
    - Logs the result of the posting operation.

    Args:
        payload (Dict[str, Any]): The JSON payload from the GitHub webhook for the edited issue event.
    """
    issue_number = payload.get("issue", {}).get("number")
    issue_title = payload.get("issue", {}).get("title", "No title")
    issue_body = payload.get("issue", {}).get("body", "No body")

    logger.info(
        "AI Bot processing edited issue:\n- Issue #%s\n- Title: %s\n- Content: %s...",
        issue_number,
        issue_title,
        issue_body[:100],
    )

    prompt = f"""
        You are an AI assistant responding to an updated GitHub issue.

        Issue Title: {issue_title}
        Updated Description: {issue_body}

        Your task:
        - Acknowledge the update
        - Briefly summarize what changed
        - Ask clarifying questions if needed
        - Keep it friendly and professional

        Generate a short, helpful response:
        """

    ai_response = _generate_response(prompt)

    if not ai_response:
        logger.error("Failed to generate AI response for edited issue.")
        return

    logger.info("Generated AI response for edited issue: %s", ai_response[:150] + "...")

    full_ai_response = f"{get_aibot_issue_analysis_comment_marker()}\n{ai_response}"

    existing_comment = find_bot_comment(issue_number, get_aibot_issue_analysis_comment_marker())

    if existing_comment:
        comment_id = existing_comment["id"]
        logger.info("Found existing bot comment. Updating it with new analysis.")
        response = post_or_patch_github_comment(issue_number, full_ai_response, comment_id)
    else:
        logger.info("No existing bot comment found. Posting a new issue analysis comment.")
        response = post_or_patch_github_comment(issue_number, full_ai_response)

    if response and response.status_code == 201:
        logger.info("AI Bot response posted successfully to edited issue #%s.", issue_number)
    else:
        logger.error(
            "Failed to post AI Bot response to edited issue #%s. Response: %s",
            issue_number,
            getattr(response, "text", "No response"),
        )


def find_bot_comment(issue_number: str, marker: str) -> Optional[dict]:
    """
    Find an existing comment made by the bot in a GitHub issue or pull request.

    Args:
        issue_number (str): The number of the GitHub issue or PR.
        marker (str): A unique string used to identify the specific bot comment.

    Returns:
        Optional[dict]: The matching comment object if found, otherwise None.
    """
    try:
        url = f"{settings.GITHUB_API_URL}/issues/{issue_number}/comments"
        headers = {
            "Authorization": f"Bearer {settings.GITHUB_AIBOT_TOKEN}",
            "Accept": "application/vnd.github+json",
        }
        response = requests.get(url, headers=headers, timeout=10)

        if response.status_code == 200:
            comments = response.json()
            bot_username = settings.GITHUB_AIBOT_USERNAME.lower()

            for comment in comments:
                author = comment.get("user", {}).get("login", "").lower()
                body = comment.get("body", "").lower()
                if author == bot_username and marker.lower() in body:
                    return comment
        else:
            logger.warning("GitHub API returned status %s while fetching comments.", response.status_code)
        return None
    except Exception as e:
        logger.error("Failed to fetch comments: %s", str(e))
        return None


def validate_payload_schema(payload: Dict[str, Any], schema: Dict[str, Any]) -> None:
    """
    Validate the payload against the provided schema.

    Args:
        payload (Dict[str, Any]): The payload to validate.
        schema (Dict[str, Any]): The JSON schema to validate against.

    Returns:
        None. Raises ValidationError if the payload does not conform to the schema, which is handled by the caller.
    """
    validate(instance=payload, schema=schema)


def get_similar_merged_chunks(
    source_collection: str, temp_collection: str, query: str, k: int, rename_mappings: Dict[str, str]
) -> List[ChunkType]:
    main_points = qdrant_client.query_points(collection_name=source_collection, query=query, limit=k)
    temp_points = qdrant_client.query_points(collection_name=temp_collection, query=query, limit=k)

    relevant_chunks = defaultdict(list)
    overwrite_log = []

    for point in main_points.points:
        chunk_data = point.payload
        key = chunk_data["file_path"]
        relevant_chunks[key] = chunk_data

    for point in temp_points.points:
        chunk_data = point.payload
        key = chunk_data["file_path"]
        if relevant_chunks[key]:
            log_entry = {
                "original_key": key,
                "action": "overwritten",
                "new_key": rename_mappings.get(key, key),
                "old_chunk_preview": relevant_chunks[key],
            }
            overwrite_log.append(log_entry)
            print(f"Found existing key: {key}. Overwriting")
            del relevant_chunks[key]
            key = rename_mappings.get(key, key)
        relevant_chunks[key] = chunk_data

    return relevant_chunks


def process_diff(diff_text: str) -> str:
    skip_files = {"package-lock.json", ".yarn.lock"}
    skip_extensions = {
        ".lock",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".pdf",
        ".zip",
        ".tar",
        ".gz",
        ".min.js",
        ".map",
        ".pyc",
        ".log",
        ".db",
        ".coverage",
        ".egg-info",
    }

    processed_diff = []

    def should_skip(file: PatchedFile) -> bool:
        return file.path in skip_files or file.path.endswith(tuple(skip_extensions)) or file.is_binary_file

    patch = PatchSet.from_string(diff_text)

    for file in patch:
        if should_skip(file):
            continue

        if file.is_added_file:
            diff_section = f"New: {file.path}\n"
            added_content = []
            for hunk in file:
                for line in hunk:
                    if line.is_added:
                        added_content.append(line.value.rstrip("\n"))
            diff_section += "\n".join(added_content) + "\n"
            processed_diff.append(diff_section)

        elif file.is_removed_file:
            diff_section = f"Removed: {file.path}\n"
            removed_content = []
            for hunk in file:
                for line in hunk:
                    if line.is_removed:
                        removed_content.append(line.value.rstrip("\n"))
            diff_section += "\n".join(removed_content) + "\n"
            processed_diff.append(diff_section)

        elif file.is_rename:
            hunk_output = []
            for hunk in file:
                hunk_output.append(str(hunk).rstrip("\n"))

            if hunk_output:
                diff_section = f"Renamed and Modified: {file.source_file[2:]} → {file.target_file[2:]}\n"
                diff_section += "\n".join(hunk_output) + "\n"
            else:
                diff_section = f"Renamed: {file.source_file[2:]} → {file.target_file[2:]}\n"
                diff_section += "\n"
            processed_diff.append(diff_section)

        elif file.is_modified_file:
            diff_section = f"Modified: {file.path}\n"
            hunk_contents = []
            for hunk in file:
                hunk_contents.append(str(hunk).rstrip("\n"))
            diff_section += "\n".join(hunk_contents) + "\n"
            processed_diff.append(diff_section)

    return "\n".join(processed_diff), patch


def get_diff_query(processed_diff: str) -> List[float]:
    template = PROMPTS["SEMANTIC_QUERY_GENERATOR_PROMPT"]
    prompt = template.replace("<DIFF>", processed_diff)
    response = generate_gemini_response(prompt)
    return response


def verify_github_signature(secret: str, payload_body: bytes, signature_header: str) -> bool:
    """
    Verifies the GitHub webhook signature using HMAC SHA256.

    Args:
        secret (str): Webhook secret key.
        payload_body (bytes): Raw request body.
        signature_header (str): Value from 'X-Hub-Signature-256' header.

    Returns:
        bool: True if the signature is valid, False otherwise.
    """
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    if not secret:
        logger.error("Webhook secret not configured; cannot verify signature.")
        return False

    try:
        received_signature = signature_header.split("=", 1)[1]
    except IndexError:
        return False

    mac = hmac.new(secret.encode(), payload_body, hashlib.sha256)
    expected_signature = mac.hexdigest()

    return hmac.compare_digest(expected_signature, received_signature)
