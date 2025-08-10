"""This module handles the GitHub AI Bot webhook events and interactions.
It processes pull requests, issues, and comments, and interacts with the
Gemini AI API to generate responses and post them on github.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import requests
from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from jsonschema import ValidationError, validate
from unidiff import PatchedFile, PatchSet

from website.aibot.aibot_env import configure_and_validate_settings, load_prompts, load_validation_schemas
from website.aibot.clients import q_client
from website.aibot.models import PullRequest
from website.aibot.network import fetch_pr_diff, generate_embedding, generate_gemini_response, post_github_comment
from website.aibot.qdrant_utils import create_temp_pr_collection, get_similar_merged_chunks
from website.aibot.utils import (
    analyze_code_ruff_bandit,
    extract_json_block,
    issue_analysis_marker,
    parse_json,
    pr_analysis_marker,
    sign_payload,
    validate_github_request,
    verify_github_signature,
)
from website.models import GithubAppInstallation, GithubAppRepo, InstallationState, RepoState

logger = logging.getLogger(__name__)

configure_and_validate_settings()


SCHEMAS = load_validation_schemas()
PROMPTS = load_prompts()
# Scalability


@require_GET
def aibot_webhook_is_healthy(request: HttpRequest) -> JsonResponse:
    github_token = settings.GITHUB_AIBOT_TOKEN
    webhook_id = settings.GITHUB_AIBOT_WEBHOOK_ID
    repo_api_url = settings.GITHUB_API_URL
    webhook_url = settings.GITHUB_AIBOT_WEBHOOK_URL
    webhook_secret = settings.GITHUB_AIBOT_WEBHOOK_SECRET

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
        payload_bytes = json.dumps(test_payload).encode("utf-8")
        signature = sign_payload(webhook_secret, payload_bytes)
        test_headers = {"X-GitHub-Event": "ping", "Content-Type": "application/json"}
        if signature:
            test_headers["X-Hub-Signature-256"] = signature
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


def handle_installation_event(payload: Dict[str, Any]) -> JsonResponse:
    # TODO Add validation schema and valdiate like other handlers
    action = payload["action"]
    installation_data = payload["installation"]
    account_data = installation_data["account"]
    sender_login = payload.get("sender", {}).get("login")
    if action == "created":
        installation, created = GithubAppInstallation.objects.get_or_create(
            installation_id=installation_data["id"],
            defaults={
                "app_id": installation_data["app_id"],
                "app_name": installation_data.get("app_slug"),
                "account_login": account_data["login"],
                "account_type": account_data["type"],
                "state": InstallationState.ACTIVE,
                "activated_at": timezone.now(),
                "activated_by_account_login": sender_login,
                "permissions": installation_data.get("permissions", {}),
                "subscribed_events": installation_data.get("events", []),
            },
        )

        processed_repos = []
        for repo_data in payload.get("repositories", []):
            repo_obj, created = GithubAppRepo.objects.update_or_create(
                repo_id=repo_data["id"],
                defaults={
                    "installation": installation,
                    "name": repo_data["name"],
                    "full_name": repo_data["full_name"],
                    "is_private": repo_data["private"],
                    "state": RepoState.PROCESSING,
                    "default_branch": "main",
                    "permissions": installation.permissions,
                },
            )
            processed_repos.append((repo_obj.full_name, created))

        created_repos = [name for name, created in processed_repos if created]
        updated_repos = [name for name, created in processed_repos if not created]

        logger.info(
            "Processed %d repositories for app %s (id=%s) installation_id=%s, account_login=%s. "
            "Created: %d, Updated: %d. Repos: %s",
            len(processed_repos),
            installation.app_name,
            installation.app_id,
            installation.installation_id,
            installation.account_login,
            len(created_repos),
            len(updated_repos),
            [name for name, _ in processed_repos],
        )

        # TODO Add logic for embedding and storing these repos in qdrant,
        # confirm if there needs to be a set limit of number of repos per user

        return JsonResponse({"success": "App installed successfully"})

    elif action in ("deleted", "suspend", "unsuspend"):
        try:
            installation = GithubAppInstallation.objects.get(installation_id=installation_data["id"])
        except GithubAppInstallation.DoesNotExist:
            sender = sender_login or "unknown"
            repo_full_name = installation_data.get("repository", {}).get("full_name", "unknown")
            action_upper = action.upper()

            logger.warning(
                "%s webhook action received for unknown installation_id=%s from sender=%s targeting repo=%s. "
                "No matching GithubAppInstallation found. Possible stale data or race condition. "
                "Verify data integrity and installation lifecycle.",
                action_upper,
                installation_data["id"],
                sender,
                repo_full_name,
            )
            return JsonResponse({"error": "Installation not found"}, status=404)

        state_mapping = {
            "deleted": ("remove", RepoState.REMOVED),
            "suspend": ("suspend", RepoState.SUSPENDED),
            "unsuspend": ("activate", RepoState.ACTIVE),
        }

        webhook_action, installation_state = state_mapping[action]
        installation.apply_webhook_state(webhook_action, sender_login)
        installation.save()
        # installation.repositories.update(state=installation_state, updated_at=timezone.now())
        logger.info(
            "%s webhook action successfully applied for installation_id=%s by sender=%s on repo=%s. "
            "State transitioned to '%s'.",
            webhook_action.upper(),
            installation_data["id"],
            sender_login or "not found",
            installation_data.get("repository", {}).get("full_name", "unknown"),
            installation_state,
        )
        return JsonResponse({"success": "App state modified successfully."})

    else:
        logger.warning(f"Unknown installation action received: {action}")
        return JsonResponse({"error": "Unsupported action."}, status=400)


def handle_installation_repositories_event(payload: Dict[str, Any]) -> JsonResponse:
    installation_id = payload["installation"]["id"]
    sender_login = payload.get("sender", {}).get("login")
    repos_added = payload.get("repositories_added", [])
    repos_removed = payload.get("repositories_removed", [])

    try:
        installation = GithubAppInstallation.objects.get(installation_id=installation_id)
    except GithubAppInstallation.DoesNotExist:
        logger.warning(
            "installation_repositories webhook received for unknown installation_id=%s from sender=%s. "
            "Repositories added: %s, removed: %s. No matching GithubAppInstallation found. "
            "This may indicate stale data, delayed webhook delivery, or an untracked installation. ",
            installation_id,
            sender_login,
            [repo.get("full_name") for repo in repos_added],
            [repo.get("full_name") for repo in repos_removed],
        )

        return JsonResponse({"error": "Installation not found."}, status=404)
    processed_repos = []

    for repo_data in repos_added:
        repo_obj, created = GithubAppRepo.objects.update_or_create(
            repo_id=repo_data["id"],
            defaults={
                "installation": installation,
                "name": repo_data["name"],
                "full_name": repo_data["full_name"],
                "is_private": repo_data["private"],
                "state": RepoState.PROCESSING,
                "default_branch": "main",
                "permissions": installation.permissions,
            },
        )
        processed_repos.append((repo_obj.full_name, created))

    created_repos = [name for name, created in processed_repos if created]
    updated_repos = [name for name, created in processed_repos if not created]

    logger.info(
        "Processed %d repositories for installation_id=%s. Created: %d, Updated: %d. Repos: %s",
        len(processed_repos),
        installation_id,
        len(created_repos),
        len(updated_repos),
        [name for name, _ in processed_repos],
    )

    repo_ids_removed = [repo["id"] for repo in repos_removed]
    if repo_ids_removed:
        GithubAppRepo.objects.filter(installation=installation, repo_id__in=repo_ids_removed).update(
            state=RepoState.REMOVED, updated_at=timezone.now()
        )
        if repo_ids_removed:
            logger.info(
                "Marked %d repositories as REMOVED for installation_id=%s. Repos: %s",
                len(repo_ids_removed),
                installation_id,
                [repo.get("full_name") for repo in repos_removed],
            )

    return JsonResponse({"status": "Repository information updated."})


def handle_repository_event(payload: Dict[str, Any]) -> JsonResponse:
    action = payload["action"]
    repo_data = payload["repository"]
    sender_login = payload.get("sender", {}).get("login")

    try:
        repo = GithubAppRepo.objects.get(repo_id=repo_data["id"])
    except GithubAppRepo.DoesNotExist:
        logger.warning(
            "Repository event received for untracked repo: %s (id=%s), action=%s, sender=%s",
            repo_data["full_name"],
            repo_data["id"],
            action,
            sender_login,
        )
        return JsonResponse({"error": "Repository not tracked"}, status=404)

    state_changes = {
        "deleted": RepoState.DELETED,
        "archived": RepoState.ARCHIVED,
        "unarchived": RepoState.ACTIVE,
        "privatized": None,
        "publicized": None,
    }

    if action in state_changes:
        if state_changes[action]:
            repo.state = state_changes[action]

        if action in ("privatized", "publicized"):
            repo.is_private = action == "privatized"

        repo.save()
        logger.info(
            "Updated repo %s (id=%s) to state=%s after %s event by sender=%s",
            repo.full_name,
            repo.repo_id,
            repo.state,
            action,
            sender_login,
        )

    elif action == "renamed":
        old_name = repo.full_name
        repo.name = repo_data["name"]
        repo.full_name = repo_data["full_name"]
        repo.save()
        logger.info(
            "Renamed repository from %s to %s (id=%s) by sender=%s",
            old_name,
            repo.full_name,
            repo.repo_id,
            sender_login,
        )

    elif action == "transferred":
        # GitHub transfers can affect permissions - may want to re-check access
        # For now just update the name if it changed. Need to learn about this in more detail,
        # but it's an edge case so can be left like this for now
        repo.name = repo_data["name"]
        repo.full_name = repo_data["full_name"]
        repo.save()
        logger.info(
            "Updated repository %s (id=%s) after transfer by sender=%s", repo.full_name, repo.repo_id, sender_login
        )

    elif action in ("created", "edited"):
        # not relevant for our uscase
        pass

    else:
        logger.warning(
            "Unhandled repository action: %s for repo %s (id=%s) by sender=%s",
            action,
            repo.full_name,
            repo.repo_id,
            sender_login,
        )
        return JsonResponse({"error": "Unsupported action"}, status=400)

    return JsonResponse({"status": "Repository updated successfully"})


def handle_ping(payload: Dict[str, Any]) -> JsonResponse:
    zen = payload.get("zen", "No zen message received.")
    logger.info("Webhook ping received: %s", zen)
    return JsonResponse({"status": "pong", "zen": zen}, status=200)


def handle_pull_request_event(payload: Dict[str, Any]) -> JsonResponse:
    validate_payload_schema(payload, SCHEMAS["PR_SCHEMA"])

    pr_instance = PullRequest(payload)
    action = pr_instance.action

    if action in ("opened", "reopened", "synchronize"):
        logger.info("Processing PR event: %r", pr_instance)
        if pr_instance._verify_branch():
            aibot_pr_opened_or_synchronize(pr_instance)
        else:
            logger.info("Skipping AI review due to branch mismatch for: %r", pr_instance)
    elif action == "closed":
        logger.debug("PR closed: %r", pr_instance)
    return JsonResponse({"status": "PR event processed"})


def handle_Issue_comment_event(payload: Dict[str, Any]) -> None:
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


EVENT_HANDLERS = {
    "ping": handle_ping,
    "pull_request": handle_pull_request_event,
    "issue_comment": handle_Issue_comment_event,
    "issue": handle_issue_event,
    "installation": handle_installation_event,
    "installation_repositories": handle_installation_repositories_event,
    "repository": handle_repository_event,
}


@csrf_exempt
@require_POST
def main_github_aibot_webhook_dispatcher(request: HttpRequest) -> JsonResponse:
    valid, err = validate_github_request(request)
    if not valid:
        logger.error("Error in validating github request: %s", err)
        return JsonResponse({"error": err})

    payload = parse_json(request.body)
    if not payload:
        logger.debug("Failed to parse payload. Raw body: %s", request.body.decode("utf-8"))
        return JsonResponse({"error": "Unable to parse payload."})

    event_type = request.headers["X-GitHub-Event"]

    logger.info("Received event: %s", event_type)
    logger.debug("Payload: %s", json.dumps(payload, indent=2, sort_keys=True))

    signature_header = request.headers.get("X-Hub-Signature-256")
    webhook_secret = settings.GITHUB_AIBOT_WEBHOOK_SECRET
    valid_sig, err_sig = verify_github_signature(webhook_secret, request.body, signature_header)
    if not valid_sig:
        logger.error("Error in validating github request: %s", err_sig)
        return JsonResponse({"error": err_sig})

    handler = EVENT_HANDLERS.get(event_type)
    if handler:
        return handler(payload)
    else:
        logger.error("No handler found for event type %s", event_type)
        return JsonResponse({"error": f"Unsupported event type {event_type}"})


def aibot_pr_opened_or_synchronize(pr_instance: PullRequest) -> None:
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
        source_collection, temp_collection = create_temp_pr_collection(pr_instance, patch)
        logger.info("Temporary collection created: %s", temp_collection)

        rename_mappings = {}
        for file in patch:
            rename_mappings[file.source_file] = file.target_file

        if source_collection and temp_collection:
            similar_chunks = get_similar_merged_chunks(
                q_client, source_collection, temp_collection, vector_query, k, rename_mappings
            )
            analysis_output = analyze_code_ruff_bandit(similar_chunks)
        else:
            logger.warning("Missing collection names: source=%s, temp=%s", source_collection, temp_collection)

        formatted_snippets = []
        for snippet in similar_chunks:
            file_path = snippet.get("file_path", "Unknown")
            chunk = snippet.get("chunk", "")
            start = snippet.get("start_line", "?")
            end = snippet.get("end_line", "?")

            formatted_snippet = f"File: {file_path}\n" f"Lines: {start}–{end}\n" f"```python\n{chunk}\n```"
            formatted_snippets.append(formatted_snippet)

        joined_snippets = "\n\n".join(formatted_snippets)

        prompt = PROMPTS["PR_REVIEWER_PROMPT"]
        placeholders = {
            "<INSERT_PR_TITLE>": pr_instance.title or "Not found",
            "<INSERT_PR_BODY>": pr_instance.body or "Not found",
            "<INSERT_PR_DIFF>": processed_diff or "Not found",
            "<INSERT_STATIC_ANALYSIS_OUTPUT>": analysis_output or "Not found",
            "<INSERT_RELEVANT_SNIPPETS>": joined_snippets or "Not found",
        }

        for key, value in placeholders.items():
            prompt = prompt.replace(key, str(value))

    bot_response = generate_gemini_response(prompt)

    if not bot_response:
        logger.error(
            "Failed to generate AI review response for new PR: %s created in %s",
            pr_instance.title,
            pr_instance.repo_full_name,
        )
    bot_response = f"{pr_analysis_marker()}\n{bot_response}"

    response = post_github_comment(pr_instance.comments_url, bot_response)

    if not response:
        logger.error("Failed to post github comment to URL: %s", pr_instance.comments_url)
    else:
        logger.info("Completed review for %r", pr_instance)


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
    response = post_github_comment(pr_number, ai_response)

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
    ai_response = generate_gemini_response(prompt)
    response = post_github_comment(issue_number, ai_response)

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

    ai_response = generate_gemini_response(prompt)

    if not ai_response:
        logger.error("Failed to generate AI response for new issue.")
        return

    logger.info("Generated AI response for new issue: %s", ai_response[:150] + "...")

    full_ai_response = f"{issue_analysis_marker()}\n{ai_response}"
    response = post_github_comment(issue_number, full_ai_response)

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

    ai_response = generate_gemini_response(prompt)

    if not ai_response:
        logger.error("Failed to generate AI response for edited issue.")
        return

    logger.info("Generated AI response for edited issue: %s", ai_response[:150] + "...")

    full_ai_response = f"{issue_analysis_marker()}\n{ai_response}"

    existing_comment = find_bot_comment(issue_number, issue_analysis_marker())

    if existing_comment:
        comment_id = existing_comment["id"]
        logger.info("Found existing bot comment. Updating it with new analysis.")
        response = post_github_comment(issue_number, full_ai_response, comment_id)
    else:
        logger.info("No existing bot comment found. Posting a new issue analysis comment.")
        response = post_github_comment(issue_number, full_ai_response)

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
