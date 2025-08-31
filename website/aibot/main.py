"""This module handles the GitHub AI Bot webhook events and interactions.
It processes pull requests, issues, and comments, and interacts with the
Gemini AI API to generate responses and post them on github.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpRequest, JsonResponse
from django.test import RequestFactory
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from jsonschema import validate

from website.aibot.aibot_env import configure_and_validate_settings
from website.aibot.constants import INSTALLATION_STATE_MAPPING, REPO_PRIVACY_UPDATES, REPO_STATE_UPDATES
from website.aibot.qdrant_api import q_rename_collection_alias
from website.aibot.tasks import (
    process_issue_comment_task,
    process_issue_task,
    process_pr_task,
    process_push_task,
    process_repos_added_task,
    process_repos_removed_task,
)
from website.aibot.utils import parse_json, sign_payload, validate_github_request, verify_github_signature
from website.aibot.validation_schemas import (
    INSTALLATION_REPOSITORIES_SCHEMA,
    INSTALLATION_SCHEMA,
    ISSUE_COMMENT_SCHEMA,
    ISSUE_SCHEMA,
    PR_SCHEMA,
    PUSH_SCHEMA,
    REPOSITORY_SCHEMA,
)
from website.models import GithubAppInstallation, GithubAppRepo, InstallationState, RepoState

logger = logging.getLogger(__name__)

APP_NAME = settings.GITHUB_AIBOT_APP_NAME


try:
    configure_and_validate_settings()
    logger.info("All settings loaded from env (Aibot App ready)")
except ImproperlyConfigured as e:
    logger.error("Couldn't setup and validate the Aibot app: %s", e)
    logger.error(
        "Due to improper configuration, the bot will not work as expected. Please review the settings and apply them."
    )


def handle_ping_event(payload: Dict[str, Any]) -> JsonResponse:
    zen = payload.get("zen", "No zen provided")
    hook_id = payload.get("hook_id", "No hook_id provided")
    return JsonResponse(
        {
            "success": True,
            "message": "Ping event received successfully.",
            "zen": zen,
            "hook_id": hook_id,
        }
    )


def handle_installation_event(payload: Dict[str, Any]) -> JsonResponse:
    validate(payload, INSTALLATION_SCHEMA)

    action = payload["action"]
    installation_data = payload["installation"]
    installation_id = installation_data["id"]
    sender_login = payload["sender"]["login"]

    if action == "created":
        installation, _ = GithubAppInstallation.objects.get_or_create(
            installation_id=installation_id,
            defaults={
                "app_id": settings.GITHUB_AIBOT_APP_ID,
                "app_name": APP_NAME,
                "account_login": installation_data["account"]["login"],
                "account_type": installation_data["account"]["type"],
                "state": InstallationState.ACTIVE,
                "activated_at": timezone.now(),
                "activated_by_account_login": sender_login,
                "permissions": installation_data.get("permissions", {}),
                "subscribed_events": installation_data.get("events", []),
            },
        )

        repos_added = payload["repositories"]

        task = process_repos_added_task.delay(installation_id, repos_added)
        logger.info(
            "Queued process_repos_added_task: task_id=%s, installation_id=%s, repos_count=%s",
            task.id,
            installation_id,
            len(repos_added),
        )

        return JsonResponse({"status": "Processed installation"})

    elif action in INSTALLATION_STATE_MAPPING:
        installation = get_installation_or_404(installation_id, sender_login, action)
        if not installation:
            return JsonResponse({"error": "Installation not found"}, status=404)

        apply_state_change(installation, action, sender_login, installation_data)

        return JsonResponse({"success": "App state modified successfully."})

    logger.warning(f"Unknown installation action received: {action}")
    return JsonResponse({"error": "Unsupported action."}, status=400)


def handle_installation_repositories_event(payload: Dict[str, Any]) -> JsonResponse:
    validate(payload, INSTALLATION_REPOSITORIES_SCHEMA)

    installation_data = payload["installation"]
    installation_id = installation_data["id"]
    sender_login = payload["sender"]["login"]
    repos_added = payload.get("repositories_added", [])
    repos_removed = payload.get("repositories_removed", [])
    event = "installation_repositories"

    installation = get_installation_or_404(installation_id, sender_login, "installation_repositories")
    if not installation:
        return JsonResponse({"error": "Installation not found"}, status=404)

    if not validate_installation_state(installation, sender_login, event):
        return JsonResponse({"error": f"Invalid installation state: {installation.state}"})

    logger.debug(
        "Offloading process_repos_added_task to Celery: installation_id=%s, app_name=%s, repos_count=%s",
        installation_id,
        APP_NAME,
        len(repos_added),
    )
    process_repos_added_task.delay(installation_id, APP_NAME, repos_added)

    logger.debug(
        "Offloading process_repos_removed_task to Celery: installation_id=%s, app_name=%s, repos_count=%s",
        installation_id,
        APP_NAME,
        len(repos_removed),
    )
    process_repos_removed_task.delay(installation_id, APP_NAME, repos_removed)

    return JsonResponse({"status": "Repository information updated."})


def handle_repository_event(payload: Dict[str, Any]) -> JsonResponse:
    validate(payload, REPOSITORY_SCHEMA)

    installation_data = payload["installation"]
    installation_id = installation_data["id"]
    action = payload["action"]
    repo_data = payload["repository"]
    sender_login = payload["sender"]["login"]
    event = "repository"

    installation = get_installation_or_404(installation_id, sender_login, event)
    if not installation:
        return JsonResponse({"error": "Installation not found."}, status=404)

    if not validate_installation_state(installation, sender_login, event):
        return JsonResponse({"error": f"Invalid installation state: {installation.state}"})

    repo = get_repo_or_404(repo_data["id"], repo_data["full_name"], action, sender_login)
    if not repo:
        return JsonResponse({"error": "Repository not tracked"}, status=404)

    SUPPORTED_ACTIONS = set(REPO_STATE_UPDATES) | set(REPO_PRIVACY_UPDATES) | {"renamed"}

    if action in SUPPORTED_ACTIONS:
        if action in REPO_STATE_UPDATES or action in REPO_PRIVACY_UPDATES:
            handle_repo_state_change(repo, action, sender_login)
        elif action == "renamed":
            handle_repo_rename(repo, repo_data, sender_login)
    else:
        logger.info(
            "Unhandled repository action: %s for repo %s (id=%s) by sender=%s",
            action,
            repo.full_name,
            repo.repo_id,
            sender_login,
        )
        return JsonResponse({"error": "Received unsupported action"}, status=400)

    return JsonResponse({"status": "Repository updated successfully"})


def handle_push_event(payload: Dict[str, Any]) -> JsonResponse:
    validate(payload, PUSH_SCHEMA)

    installation_id = payload["installation"]["id"]
    repo_data = payload["repository"]
    repo_id = repo_data["id"]
    repo_full_name = repo_data["full_name"]
    base_commit_sha, head_commit_sha = payload["before"], payload["after"]
    sender_login = payload["sender"]["login"]
    event = "push"
    action = event  # Push event doesn't have action field

    installation = get_installation_or_404(installation_id, sender_login, event)
    if not installation:
        return JsonResponse({"error": "Installation not found."}, status=404)

    if not validate_installation_state(installation, sender_login, event):
        return JsonResponse({"error": f"Invalid installation state: {installation.state}"})

    repo = get_repo_or_404(repo_data["id"], repo_data["full_name"], action, sender_login)
    if not repo:
        return JsonResponse({"error": "Repository not tracked"}, status=404)

    if not validate_repo_state(repo, sender_login, action):
        return JsonResponse({"error": f"Invalid repository state: {repo.state}"}, status=404)

    logger.info("Offloading process_push_task to Celery: installation_id=%s, repo_full_name=%s")
    process_push_task.delay(installation_id, repo_id, repo_full_name, base_commit_sha, head_commit_sha)

    return JsonResponse({"success": "Processed push event successfully"})


def handle_pull_request_event(payload: Dict[str, Any]) -> JsonResponse:
    validate(payload, PR_SCHEMA)

    action = payload["action"]
    installation_data = payload["installation"]
    installation_id = installation_data["id"]
    repo_data = payload["repository"]
    repo_id = repo_data["id"]
    repo_full_name = repo_data["full_name"]
    pr_number = payload["number"]
    sender_login = payload["sender"]["login"]
    event = "pull_request"
    is_draft = payload["pull_request"]["draft"]

    if is_draft:
        logger.debug("PR #%s is draft, not posting review.", pr_number)
        return JsonResponse({"status": "Ignored due to draft PR."}, status=404)

    installation = get_installation_or_404(installation_id, sender_login, event)
    if not installation:
        return JsonResponse({"error": "Installation not found."}, status=404)

    if not validate_installation_state(installation, sender_login, event):
        return JsonResponse({"error": f"Invalid installation state: {installation.state}"})

    repo = get_repo_or_404(repo_id, repo_full_name, action, sender_login)
    if not repo:
        return JsonResponse({"error": "Repository not tracked"}, status=404)

    if not validate_repo_state(repo, sender_login, action):
        return JsonResponse({"error": f"Invalid repository state: {repo.state}"}, status=404)

    if action in {
        "opened",
        "ready_for_review",
        "synchronize",
    }:
        logger.info(
            "Offloading pr analysis task to Celery: installation_id=%s, repo_full_name=%s",
            installation_id,
            repo_full_name,
        )
        process_pr_task.delay(installation_id, repo_id, action, payload)
    elif action == "closed":
        logger.debug("PR was closed: %s in %s", pr_number, repo_full_name)
    else:
        logger.debug("Ignoring unhandled PR action: %s for pr #%s in %s", action, pr_number, repo_full_name)
    return JsonResponse({"status": "PR event processed"})


def handle_issue_comment_event(payload: Dict[str, Any]) -> None:
    validate(payload, ISSUE_COMMENT_SCHEMA)

    installation_id = payload["installation"]["id"]
    repo_data = payload["repository"]
    repo_id = repo_data["id"]
    sender_login = payload["sender"]["login"]

    if sender_login == f"{APP_NAME}[bot]":
        logger.debug("This event is by blt-aibot's comment. Ignoring")
        return JsonResponse({"status": "Ignoring blt-aibot's own comment"})

    action = payload["action"]
    comment_body = payload["comment"]["body"]
    issue = payload["issue"]

    event = "issue_comment"

    installation = get_installation_or_404(installation_id, sender_login, event)
    if not installation:
        return JsonResponse({"error": "Installation not found."}, status=404)

    if not validate_installation_state(installation, sender_login, event):
        return JsonResponse({"error": f"Invalid installation state: {installation.state}"})

    repo = get_repo_or_404(repo_data["id"], repo_data["full_name"], action, sender_login)
    if not repo:
        return JsonResponse({"error": "Repository not tracked"}, status=404)

    if not validate_repo_state(repo, sender_login, action):
        return JsonResponse({"error": f"Invalid repository state: {repo.state}"}, status=404)

    bot_name = APP_NAME.lower()
    mention_string = f"@{bot_name}"
    if mention_string not in comment_body:
        logger.debug("%s was not mentioned in comment. Ignoring", bot_name)
        return JsonResponse({"status": f"{bot_name} was not mentioned in comment. Ignoring"})

    if action == "created":
        logger.info(
            "Offloading issue analysis task to Celery: installation_id=%s, repo_full_name=%s",
            installation_id,
            repo_data["full_name"],
        )
        process_issue_comment_task.delay(installation_id, repo_id, issue, sender_login)
    else:
        logger.debug("Ignoring issue event with action=%s", action)
    return JsonResponse({"status": "Processed issue comment event"})


def handle_issues_event(payload: Dict[str, Any]) -> JsonResponse:
    validate(payload, ISSUE_SCHEMA)

    installation_data = payload["installation"]
    installation_id = installation_data["id"]
    repo_data = payload["repository"]
    repo_id = payload["id"]
    sender_login = payload["sender"]["login"]
    action = payload["action"]
    issue = payload["issue"]
    event = "issues"

    installation = get_installation_or_404(installation_id, sender_login, event)
    if not installation:
        return JsonResponse({"error": "Installation not found."}, status=404)

    if not validate_installation_state(installation, sender_login, event):
        return JsonResponse({"error": f"Invalid installation state: {installation.state}"})

    repo = get_repo_or_404(repo_data["id"], repo_data["full_name"], action, sender_login)
    if not repo:
        return JsonResponse({"error": "Repository not tracked"}, status=404)

    if not validate_repo_state(repo, sender_login, action):
        return JsonResponse({"error": f"Invalid repository state: {repo.state}"}, status=404)

    if action in {"opened", "edited"}:
        process_issue_task.delay(installation_id, repo_id, action, issue, sender_login)
    else:
        logger.debug("Ignoring issue event with action=%s", action)
    return JsonResponse({"success": "processed"})


def get_handler(event_type: str):
    EVENT_HANDLERS = {
        "ping": handle_ping_event,
        "pull_request": handle_pull_request_event,
        "issue_comment": handle_issue_comment_event,
        "issues": handle_issues_event,
        "installation": handle_installation_event,
        "installation_repositories": handle_installation_repositories_event,
        "repository": handle_repository_event,
        "push": handle_push_event,
    }

    return EVENT_HANDLERS.get(event_type)


@csrf_exempt
@require_POST
def aibot_webhook_entrypoint(request: HttpRequest) -> JsonResponse:
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
    logger.debug("Received payload: %s", json.dumps(payload, indent=2, sort_keys=True))

    signature_header = request.headers.get("X-Hub-Signature-256")
    webhook_secret = settings.GITHUB_AIBOT_WEBHOOK_SECRET
    valid_sig, err_sig = verify_github_signature(webhook_secret, request.body, signature_header)
    if not valid_sig:
        logger.error("Error in validating github request: %s", err_sig)
        return JsonResponse({"error": err_sig})

    handler = get_handler(event_type)
    if handler:
        logger.debug("Dispatching event '%s' to handler '%s'", event_type, handler.__name__)
        return handler(payload)
    else:
        logger.error("No handler found for event type %s", event_type)
        return JsonResponse({"error": f"Unsupported event type {event_type}"})


@csrf_exempt
@require_GET
def aibot_health_check(request: HttpRequest) -> JsonResponse:
    """
    Health check endpoint that simulates a GitHub ping event and calls
    aibot_webhook_entrypoint to verify end-to-end functionality.
    Returns:
        JsonResponse with:
        - health: 1 (ok), 2 (error)
        - status: user-friendly message
        - last_checked: timestamp
        - error: if any
    """
    try:
        test_payload = {"zen": "Keep it logically awesome", "hook_id": "health-check"}
        payload_bytes = json.dumps(test_payload).encode("utf-8")

        secret = settings.GITHUB_AIBOT_WEBHOOK_SECRET
        signature = sign_payload(secret, payload_bytes)
        if not signature:
            return JsonResponse(
                {
                    "health": 2,
                    "status": "Failed to sign payload",
                    "error": "Webhook secret missing or signing failed",
                    "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
                status=500,
            )

        factory = RequestFactory()
        fake_request = factory.post(
            "/webhooks/github/aibot/",
            data=payload_bytes,
            content_type="application/json",
            **{
                "HTTP_X_GITHUB_EVENT": "ping",
                "HTTP_X_HUB_SIGNATURE_256": signature,
            },
        )

        webhook_response = aibot_webhook_entrypoint(fake_request)

        try:
            webhook_data = json.loads(webhook_response.content)
        except Exception as e:
            return JsonResponse(
                {
                    "health": 2,
                    "status": "Invalid response from webhook",
                    "error": "Failed to parse webhook response",
                    "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
                status=500,
            )
        if webhook_response.status_code != 200:
            return JsonResponse(
                {
                    "health": 2,
                    "status": "Webhook endpoint returned error",
                    "error": f"Status {webhook_response.status_code}: {webhook_data.get('error', 'Unknown error')}",
                    "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
                status=500,
            )
        return JsonResponse(
            {
                "health": 1,
                "status": "Webhook is operational and responded successfully",
                "webhook_response": webhook_data,
                "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    except Exception as e:
        return JsonResponse(
            {
                "health": 2,
                "status": "Health check failed",
                "error": "Unknown error",
                "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
            status=500,
        )


def get_installation_or_404(installation_id: str, sender_login: str, action_desc: str) -> GithubAppInstallation | None:
    try:
        return GithubAppInstallation.objects.get(installation_id=installation_id)
    except GithubAppInstallation.DoesNotExist:
        logger.warning(
            "%s webhook for unknown installation_id=%s by %s. Possible stale data or untracked installation.",
            action_desc,
            installation_id,
            sender_login or "unknown",
        )
        return None


def get_repo_or_404(repo_id: str, repo_full_name: str, action: str, sender_login: str) -> GithubAppRepo | None:
    try:
        return GithubAppRepo.objects.get(repo_id=repo_id)
    except GithubAppRepo.DoesNotExist:
        logger.warning(
            "Repository event '%s' for untracked repo: %s (id=%s), sender=%s",
            action,
            repo_full_name,
            repo_id,
            sender_login,
        )
        return None


def validate_installation_state(installation: GithubAppInstallation, sender_login: str, action: str) -> bool:
    if installation.state != InstallationState.ACTIVE:
        logger.error(
            "Received event for invalid installation state=%s, id=%s by sender=%s for action=%s",
            installation.state,
            installation.installation_id,
            sender_login,
            action,
        )
        return False
    return True


def validate_repo_state(repo: GithubAppRepo, sender_login: str, action: str) -> bool:
    if repo.state != RepoState.ACTIVE:
        logger.error(
            "Received event for invalid repo state=%s, repo=%s, installation id=%s by sender=%s for action=%s",
            repo.state,
            repo.full_name,
            repo.installation_id,
            sender_login,
            action,
        )
        return False
    return True


def handle_repo_rename(repo: GithubAppRepo, repo_data: Dict[str, Any], sender_login: str) -> None:
    """
    Handle repository rename events:
    - Update the repo object in DB.
    - Rename the Qdrant alias pointing to its collection.

    Args:
        repo: Repo model instance.
        repo_data: Incoming data containing new name and full_name.
        sender_login: User who triggered the rename.
    """
    old_name = repo.full_name

    repo.name = repo_data["name"]
    repo.full_name = repo_data["full_name"]
    repo.save()

    try:
        q_rename_collection_alias(
            old_name=old_name,
            new_name=repo_data["full_name"],
            repo_id=repo_data["id"],
        )
        logger.info(
            "Renamed repository from '%s' to '%s' (id=%s) by sender=%s",
            old_name,
            repo_data["full_name"],
            repo_data["id"],
            sender_login,
        )
    except ValueError as e:
        logger.warning("No Qdrant collection to rename for repo '%s': %s", old_name, e)
    except Exception as e:
        logger.error("Unexpected error renaming Qdrant collection: %s", e)


def propagate_installation_state_change(installation: GithubAppInstallation, webhook_action: str):
    repos = installation.repositories.all()

    if webhook_action in ["remove", "suspend"]:
        repo_payloads = [
            {
                "id": r.repo_id,
                "name": r.name,
                "full_name": r.full_name,
                "private": r.is_private,
                "default_branch": r.default_branch,
            }
            for r in repos
        ]

        process_repos_removed_task.delay(installation.installation_id, repo_payloads)
        logger.info(
            "Triggered %s for %s repositories on installation %s.",
            "removal" if webhook_action == "remove" else "suspension",
            len(repo_payloads),
            installation.installation_id,
        )

        # NOTE: the process_repos_removed_task marks all repos as REMOVED even if event was SUSPENDED.
        # For more accurate status, can make it flexible with state updates by passing the actual action.

    elif webhook_action == "activate":
        to_process = repos.exclude(state=RepoState.ACTIVE)
        repo_payloads = [
            {
                "id": r.repo_id,
                "name": r.name,
                "full_name": r.full_name,
                "private": r.is_private,
                "default_branch": r.default_branch,
            }
            for r in to_process
        ]
        if repo_payloads:
            process_repos_added_task.delay(installation.installation_id, repo_payloads)
        logger.info("Triggered reprocessing for %s repos on activation.", len(repo_payloads))


def apply_state_change(
    installation: GithubAppInstallation, action: str, sender_login: str, installation_data: Dict[str, Any]
) -> JsonResponse:
    webhook_action, installation_state = INSTALLATION_STATE_MAPPING[action]

    installation.apply_webhook_state(webhook_action, sender_login)
    installation.save()

    logger.info(
        "%s webhook action applied for installation_id=%s. State: '%s'.",
        webhook_action.upper(),
        installation_data["id"],
        installation_state,
    )

    propagate_installation_state_change(installation, webhook_action)

    return JsonResponse({"status": "ok"})


def handle_repo_state_change(repo: GithubAppRepo, action: str, sender_login: str) -> None:
    if action in REPO_STATE_UPDATES:
        repo.state = REPO_STATE_UPDATES[action]

    if action in REPO_PRIVACY_UPDATES:
        repo.is_private = REPO_PRIVACY_UPDATES[action]

    repo.save()
    logger.info(
        "Updated repo %s (id=%s) to state=%s, is_private=%s after %s event by sender=%s",
        repo.full_name,
        repo.repo_id,
        repo.state,
        repo.is_private,
        action,
        sender_login,
    )
