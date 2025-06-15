import hashlib
import hmac
import json
import logging
import random
import time
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from jsonschema import ValidationError, validate

logger = logging.getLogger(__name__)

MAX_RETRIES = 5
RETRY_BACKOFF = 2

with open("website/schemas/aibot_comment_schema.json", "r") as f:
    AIBOT_COMMENT_SCHEMA = json.load(f)
with open("website/schemas/aibot_issue_schema.json", "r") as f:
    AIBOT_ISSUE_SCHEMA = json.load(f)
with open("website/schemas/aibot_pr_schema.json", "r") as f:
    AIBOT_PR_SCHEMA = json.load(f)


def _get_setting(key_name):
    value = getattr(settings, key_name, None)
    if not value:
        logger.error(f"[CONFIG ERROR] Setting '{key_name}' is missing or empty.")
    return value


def get_gemini_api_key():
    return _get_setting("GEMINI_API_KEY")


def get_github_token():
    return _get_setting("GITHUB_TOKEN")


def get_github_url():
    return _get_setting("GITHUB_URL")


def get_github_api_url():
    return _get_setting("GITHUB_API_URL")


def get_github_aibot_webhook_url():
    return _get_setting("GITHUB_AIBOT_WEBHOOK_URL")


def get_github_aibot_webhook_id():
    return _get_setting("GITHUB_AIBOT_WEBHOOK_ID")


def get_github_aibot_webhook_secret():
    return _get_setting("GITHUB_AIBOT_WEBHOOK_SECRET")


def get_github_aibot_token():
    return _get_setting("GITHUB_AIBOT_TOKEN")


def get_github_aibot_username():
    return _get_setting("GITHUB_AIBOT_USERNAME")


# _client_instance = None


# def get_genai_client():
#     global _client_instance
#     if _client_instance is None:
#         genai.configure(api_key=get_gemini_api_key())
#         _client_instance = genai.GenerativeModel("gemini-2.5-flash")
#     return _client_instance


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
    required_settings = ["GITHUB_TOKEN", "GITHUB_AIBOT_WEBHOOK_ID", "GITHUB_API_URL", "GITHUB_AIBOT_WEBHOOK_URL"]

    missing_settings = [s for s in required_settings if not hasattr(settings, s)]
    if missing_settings:
        logger.error("Configuration error - Missing settings: %s", missing_settings)
        return JsonResponse(
            {"health": "3", "status": "Configuration error", "message": "Required settings are missing"}, status=500
        )

    github_token = get_github_token()
    webhook_id = get_github_aibot_webhook_id()
    repo_api_url = get_github_api_url().rstrip("/")
    webhook_url = get_github_aibot_webhook_url()

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
                "repo": get_github_url(),
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

    webhook_secret = get_github_aibot_webhook_secret()
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
    """Validate and handle pull request related events (opened, synchronize)."""
    validate_payload_schema(payload, AIBOT_PR_SCHEMA)
    action = payload.get("action")
    pr_data = payload.get("pull_request", {})
    if action == "opened":
        logger.info("New PR opened: #%s - %s", pr_data.get("number"), pr_data.get("title"))
        aibot_handle_new_pr_opened(payload)
    elif action == "synchronize":
        logger.info("PR updated: #%s - New commits pushed", pr_data.get("number"))
        aibot_handle_pr_update(payload)
    return JsonResponse({"status": "PR event processed"})


def handle_comment_event(payload: Dict[str, Any]) -> None:
    """
    Validate and handle comments on PRs/issues where the bot might be mentioned.
    Ignores comments made by the bot itself (present in the validation schema).
    """
    validate_payload_schema(payload, AIBOT_COMMENT_SCHEMA)
    comment = payload.get("comment", {})
    comment_body = comment.get("body", "").lower()

    logger.info(
        "Processing comment event:\n- Comment ID: %s\n- Body: %s\n- User: %s",
        comment.get("id"),
        comment_body[:50],
        comment.get("user", {}).get("login", "unknown"),
    )

    if comment.get("user", {}).get("login") == get_github_aibot_username():
        logger.info("Ignoring comment made by the AI Bot itself.")
        return

    if f"@{get_github_aibot_username()}" in comment_body:
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
    validate_payload_schema(payload, AIBOT_ISSUE_SCHEMA)
    action = payload.get("action")
    issue_data = payload.get("issue", {})
    if action == "opened":
        logger.info("New issue opened: #%s - %s", issue_data.get("number"), issue_data.get("title"))
        aibot_handle_new_issue(payload)
    elif action == "edited":
        logger.info("Issue edited: #%s - %s", issue_data.get("number"), issue_data.get("title"))
        aibot_handle_issue_edited(payload)
    return JsonResponse({"status": "Issue event processed"})


AIBOT_PR_ANALYSIS_COMMENT_MARKER = f"**PR Analysis by {get_github_aibot_username()}**"
AIBOT_ISSUE_ANALYSIS_COMMENT_MARKER = f"**Issue Analysis by {get_github_aibot_username()}**"


def aibot_handle_new_pr_opened(payload: Dict[str, Any]) -> None:
    """This function handles the logic when a new PR is opened."""
    logger.info("Handling new PR opened.")
    pr = payload.get("pull_request", {})
    pr_number = pr.get("number")
    pr_title = pr.get("title", "No title")
    pr_body = pr.get("body", "No body")
    pr_diff_url = pr.get("diff_url", "")

    context = f"PR Title: {pr_title}\nPR Body: {pr_body}\n"

    pr_diff = fetch_info(pr_diff_url)
    if pr_diff:
        cleaned_diff = clean_diff(pr_diff)
        context += f"PR Diff:\n{cleaned_diff[:100]}...\n"
    else:
        context += "PR Diff: Unable to fetch diff.\n"

    logger.info("Context for AI Bot: %s", context)
    ai_response = (
        f"{AIBOT_PR_ANALYSIS_COMMENT_MARKER}\n I noticed that a new PR was opened. Here are the details:\n{context}"
    )
    logger.info("AI Bot response: %s", ai_response)

    response = post_or_patch_github_comment(pr_number, ai_response)
    if response and response.status_code == 201:
        logger.info("AI Bot response posted successfully: %s", ai_response)
    else:
        logger.error("Failed to post AI Bot response. Response: %s", getattr(response, "text", "No response"))


def aibot_handle_pr_update(payload: Dict[str, Any]) -> None:
    """This function handles the logic when a PR is updated with new commits."""
    logger.info("Handling PR update.")
    pr = payload.get("pull_request", {})
    pr_number = pr.get("number")
    pr_title = pr.get("title", "No title")
    pr_diff_url = pr.get("diff_url", "")

    context = f"PR Title: {pr_title}\n"

    pr_diff = fetch_info(pr_diff_url)
    if pr_diff:
        cleaned_diff = clean_diff(pr_diff)
        context += f"Changes in Update:\n{cleaned_diff[:100]}...\n"
    else:
        context += "Unable to fetch changes.\n"

    ai_response = f"{AIBOT_PR_ANALYSIS_COMMENT_MARKER}\n I noticed that the PR was updated with new commits. Here are the details:\n{context}"
    logger.info("AI Bot response: %s", ai_response)

    existing_comment = find_bot_comment(pr_number, AIBOT_PR_ANALYSIS_COMMENT_MARKER)
    if existing_comment:
        comment_id = existing_comment.get("id")
        response = post_or_patch_github_comment(pr_number, ai_response, comment_id)
    else:
        logger.info("No existing bot comment found. Posting a new PR analysis comment.")
        comment_id = None
        logger.info("Posting new AI Bot comment: %s", ai_response)

    response = post_or_patch_github_comment(pr_number, ai_response, comment_id)
    if response and response.status_code == 201:
        logger.info("AI Bot response posted successfully: %s", ai_response)
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

    ai_response = f"Hello @{commenter}, I received your comment on this issue! Here's a sample reply."
    response = post_or_patch_github_comment(issue_number, ai_response)

    if response and response.status_code == 201:
        logger.info("AI Bot response posted successfully to issue comment.")
    else:
        logger.error(
            "Failed to post AI Bot response to issue comment. Response: %s", getattr(response, "text", "No response")
        )


def aibot_handle_new_issue(payload: Dict[str, Any]) -> None:
    """Handle newly opened issues."""
    issue_number = payload.get("issue", {}).get("number")
    issue_title = payload.get("issue", {}).get("title", "No title")
    issue_body = payload.get("issue", {}).get("body", "No body")

    logger.info(
        "AI Bot processing new issue:\n- Issue #%s\n- Title: %s\n- Content: %s...",
        issue_number,
        issue_title,
        issue_body[:100],
    )

    ai_response = f"{AIBOT_ISSUE_ANALYSIS_COMMENT_MARKER}\n Thanks for opening this issue! This is a sample response while I analyze the problem: **{issue_title}**"

    response = post_or_patch_github_comment(issue_number, ai_response)

    if response and response.status_code == 201:
        logger.info("AI Bot response posted successfully to new issue.")
    else:
        logger.error(
            "Failed to post AI Bot response to new issue. Response: %s", getattr(response, "text", "No response")
        )


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

    ai_response = f"{AIBOT_ISSUE_ANALYSIS_COMMENT_MARKER}\n Thanks for updating this issue! This is a sample response while I analyze the problem: **{issue_title}**"

    existing_comment = find_bot_comment(issue_number, AIBOT_ISSUE_ANALYSIS_COMMENT_MARKER)

    if existing_comment:
        comment_id = existing_comment.get("id")
        logger.info("Found existing bot comment. Updating it with new analysis.")
        response = post_or_patch_github_comment(issue_number, ai_response, comment_id)
    else:
        logger.info("No existing bot comment found. Posting a new issue analysis comment.")
        logger.info("Posting new AI Bot comment: %s", ai_response)
        response = post_or_patch_github_comment(issue_number, ai_response)

    logger.info("Posting AI Bot response to edited issue: %s", ai_response)

    if response and response.status_code == 201:
        logger.info("AI Bot response posted successfully to edited issue.")
    else:
        logger.error(
            "Failed to post AI Bot response to edited issue. Response: %s", getattr(response, "text", "No response")
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
        url = f"{get_github_api_url()}/issues/{issue_number}/comments"
        headers = {
            "Authorization": f"Bearer {get_github_aibot_token()}",
            "Accept": "application/vnd.github+json",
        }
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            comments = response.json()
            bot_username = get_github_aibot_username().lower()

            for comment in comments:
                author = comment.get("user", {}).get("login", "").lower()
                body = comment.get("body", "").lower()
                if author == bot_username and marker.lower() in body:
                    return comment
        else:
            logger.warning("GitHub API returned status %s while fetching comments.", response.status_code)
        return None
    except Exception as e:
        logger.error(f"Failed to fetch comments: {e}")
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


def post_or_patch_github_comment(
    issue_number: str, comment: str, comment_id: Optional[str] = None
) -> Optional[requests.Response]:
    """
    Post a new comment or patch an existing one on a GitHub issue/pull request.

    Args:
        issue_number (str): The issue or pull request number.
        comment (str): The comment body to post or update.
        comment_id (Optional[str]): If present, edits the existing comment with this ID.

    Returns:
        Optional[requests.Response]: The response object if the request succeeds, otherwise None.

    Retries:
        Retries up to MAX_RETRIES times on network errors or transient server errors (HTTP 502, 503, 504),
        with exponential backoff.
    """
    if not issue_number or not comment.strip():
        logger.error("Invalid input: empty issue number or comment.")
        return None

    if comment_id:
        url = f"{get_github_api_url()}/issues/comments/{comment_id}"
    else:
        url = f"{get_github_api_url()}/issues/{issue_number}/comments"

    headers = {
        "Authorization": f"Bearer {get_github_aibot_token()}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": f"{get_github_aibot_username()}/1.0",
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            method = requests.patch if comment_id else requests.post
            response = method(url, json={"body": comment}, headers=headers, timeout=10)
            logger.info("Attempt %d to %s comment on #%s", attempt, "update" if comment_id else "post", issue_number)

            if response.status_code == 201 or (response.status_code == 200 and comment_id):
                logger.info(
                    "%s comment successfully posted/updated on #%s", "Updated" if comment_id else "Posted", issue_number
                )
                return response
            elif response.status_code in {502, 503, 504}:
                logger.warning(
                    "Transient error (%s). Retrying attempt %d/%d...", response.status_code, attempt, MAX_RETRIES
                )
            elif response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
                reset_time = int(response.headers.get("X-RateLimit-Reset", "0"))
                sleep_seconds = max(reset_time - int(time.time()), 0)
                logger.warning("Rate limit exceeded. Sleeping for %d seconds...", sleep_seconds)
                time.sleep(sleep_seconds)
                continue
            else:
                logger.error(
                    "Failed to %s comment. Status: %s, Response: %s",
                    "update" if comment_id else "post",
                    response.status_code,
                    response.text,
                )
                return response

        except requests.RequestException as e:
            logger.exception("Network error on attempt %d/%d: %s", attempt, MAX_RETRIES, str(e))

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_BACKOFF * attempt + random.uniform(0, 1))

    logger.error(
        "All retry attempts failed for %s comment on #%s", "updating" if comment_id else "posting", issue_number
    )
    return None


def clean_diff(diff_text: str) -> str:
    lines = diff_text.split("\n")
    cleaned_lines = []
    for line in lines:
        if line.startswith(("index", "---", "+++", "@@")):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


ALLOWED_DOMAINS = {"github.com"}


def fetch_info(url: str) -> Optional[str]:
    """
    Securely fetches data from allowed domains, handling both diff and JSON responses.
    """
    try:
        parsed_url = urlparse(url)
        if parsed_url.netloc not in ALLOWED_DOMAINS:
            logger.error("Blocked request to unauthorized domain: %s", parsed_url.netloc)
            return None

        headers = {"Authorization": f"Bearer {get_github_aibot_token()}", "Accept": "application/vnd.github.v3+json"}
        response = requests.get(url, headers=headers, allow_redirects=False, timeout=10)
        response.raise_for_status()

        return response.text if url.endswith(".diff") else response.json()

    except requests.RequestException as e:
        logger.error("Error fetching data from %s: %s", url, str(e))
        return None


def verify_github_signature(secret: str, payload_body: str, signature_header: str) -> bool:
    """
    Verifies GitHub webhook signature.

    Args:
        secret (str): The webhook secret key.
        payload_body (bytes): The raw request body.
        signature_header (str): The value of the 'X-Hub-Signature-256' header.

    Returns:
        bool: True if signature matches, else False.
    """
    if not signature_header or signature_header == "":
        return False

    # Remove "sha256=" prefix
    signature = signature_header.split("=")[1]

    mac = hmac.new(key=secret.encode(), msg=payload_body, digestmod=hashlib.sha256)
    expected_signature = mac.hexdigest()

    return hmac.compare_digest(expected_signature, signature)
