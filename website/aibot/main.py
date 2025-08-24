"""This module handles the GitHub AI Bot webhook events and interactions.
It processes pull requests, issues, and comments, and interacts with the
Gemini AI API to generate responses and post them on github.
"""

import json
import logging
from typing import Any, Dict, List, Tuple

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from jsonschema import validate

from website.aibot.aibot_env import configure_and_validate_settings
from website.aibot.constants import INSTALLATION_STATE_MAPPING, REPO_STATE_CHANGES
from website.aibot.gemini_api import generate_embedding, generate_gemini_response
from website.aibot.github_api import GitHubClient, GitHubTokenManager
from website.aibot.models import PullRequest
from website.aibot.prompt_templates import (
    CONVERSATION_QUERY_GENERATOR,
    ISSUE_COMMENT_RESPONDER,
    ISSUE_PLANNER,
    ISSUE_QUERY,
    PR_QUERY_GENERATOR,
    PR_REVIEWER,
)
from website.aibot.qdrant_api import (
    create_temp_pr_collection,
    q_collection_exists,
    q_get_collection_name,
    q_get_similar_chunks,
    q_get_similar_merged_chunks,
    q_process_changed_files,
    q_process_remote_repo,
    rename_qdrant_collection_with_alias,
)
from website.aibot.types import ChunkType, EmbeddingTaskType
from website.aibot.utils import (
    analyze_code_ruff_bandit,
    approximate_token_count_char,
    extract_json_block,
    format_chunks_to_string,
    issue_analysis_marker,
    parse_json,
    pr_analysis_marker,
    process_diff,
    validate_github_request,
    verify_github_signature,
)
from website.aibot.validation_schemas import (
    INSTALLATION_REPOSITORIES_SCHEMA,
    INSTALLATION_SCHEMA,
    ISSUE_COMMENT_SCHEMA,
    ISSUE_SCHEMA,
    PR_SCHEMA,
    PUSH_SCHEMA,
    REPOSITORY_SCHEMA,
)
from website.models import AibotComment, GithubAppInstallation, GithubAppRepo, InstallationState, RepoState

logger = logging.getLogger(__name__)

configure_and_validate_settings()

_token_manager = None


def get_token_manager():
    global _token_manager
    if _token_manager is None:
        _token_manager = GitHubTokenManager(
            settings.GITHUB_AIBOT_APP_ID, settings.GITHUB_AIBOT_APP_NAME, settings.GITHUB_AIBOT_PRIVATE_KEY_B64
        )
    return _token_manager


# TODO: Create health function/api


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
    sender_login = payload.get("sender", {}).get("login")
    gh_client = GitHubClient(installation_id, installation_data["app_slug"], get_token_manager())

    if action == "created":
        installation, _ = GithubAppInstallation.objects.get_or_create(
            installation_id=installation_id,
            defaults={
                "app_id": installation_data["app_id"],
                "app_name": installation_data["app_slug"],
                "account_login": installation_data["account"]["login"],
                "account_type": installation_data["account"]["type"],
                "state": InstallationState.ACTIVE,
                "activated_at": timezone.now(),
                "activated_by_account_login": sender_login,
                "permissions": installation_data.get("permissions", {}),
                "subscribed_events": installation_data.get("events", []),
            },
        )

        processed_repos, failed_repos = [], []
        for repo in payload.get("repositories", []):
            success, failed = process_repository(repo, installation, gh_client)
            if success:
                processed_repos.append(success)
            if failed:
                failed_repos.append(failed)

        return JsonResponse({"success": True, "processed_repos": processed_repos, "failed_repos": failed_repos})

    elif action in INSTALLATION_STATE_MAPPING:
        installation = get_installation_or_404(installation_id, sender_login, action)
        if not installation:
            return JsonResponse({"error": "Installation not found"}, status=404)
        return apply_state_change(installation, action, sender_login, installation_data)

    logger.warning(f"Unknown installation action received: {action}")
    return JsonResponse({"error": "Unsupported action."}, status=400)


def handle_installation_repositories_event(payload: Dict[str, Any]) -> JsonResponse:
    validate(payload, INSTALLATION_REPOSITORIES_SCHEMA)

    installation_data = payload["installation"]
    installation_id = installation_data["id"]
    sender_login = payload.get("sender", {}).get("login")
    repos_added = payload.get("repositories_added", [])
    repos_removed = payload.get("repositories_removed", [])

    gh_client = GitHubClient(installation_id, installation_data["app_slug"], get_token_manager())
    event = "installation_repositories"

    installation = get_installation_or_404(installation_id, sender_login, event)
    if not installation:
        return JsonResponse({"error": "Installation not found"}, status=404)

    created_repos, updated_repos = [], []

    for repo_data in repos_added:
        repo_obj, created = ensure_repo_entry(repo_data, installation, gh_client)
        (created_repos if created else updated_repos).append(repo_obj.full_name)

    if created_repos or updated_repos:
        logger.info(
            "Processed %d repositories for installation_id=%s. Created: %d, Updated: %d. Repos: %s",
            len(created_repos) + len(updated_repos),
            installation_id,
            len(created_repos),
            len(updated_repos),
            created_repos + updated_repos,
        )

    if repos_removed:
        repo_ids_removed = [repo["id"] for repo in repos_removed]
        GithubAppRepo.objects.filter(installation=installation, repo_id__in=repo_ids_removed).update(
            state=RepoState.REMOVED, updated_at=timezone.now()
        )

        logger.info(
            "Marked %d repositories as REMOVED for installation_id=%s. Repos: %s",
            len(repo_ids_removed),
            installation_id,
            [repo["full_name"] for repo in repos_removed],
        )

    return JsonResponse({"status": "Repository information updated."})


def handle_repository_event(payload: Dict[str, Any]) -> JsonResponse:
    validate(payload, REPOSITORY_SCHEMA)

    installation_data = payload["installation"]
    installation_id = installation_data["id"]
    action = payload["action"]
    repo_data = payload["repository"]
    sender_login = payload.get("sender", {}).get("login")
    event = "repository"

    installation = get_installation_or_404(installation_id, sender_login, event)
    if not installation:
        return JsonResponse({"error": "Installation not found."}, status=404)

    if not validate_installation_state(installation, sender_login, event):
        return JsonResponse({"error": f"Invalid installation state: {installation.state}"})

    repo = get_repo_or_404(repo_data["id"], repo_data["full_name"], action, sender_login)
    if not repo:
        return JsonResponse({"error": "Repository not tracked"}, status=404)

    if action in REPO_STATE_CHANGES:
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
        return JsonResponse({"error": "Unsupported action"}, status=400)

    return JsonResponse({"status": "Repository updated successfully"})


def handle_push_event(payload: Dict[str, Any]) -> JsonResponse:
    validate(payload, PUSH_SCHEMA)

    installation_id = payload["installation"]["id"]
    action = payload["action"]
    repo_data = payload["repository"]
    repo_full_name = repo_data["full_name"]
    before, after = payload["before"], payload["after"]
    sender_login = payload["sender"]["login"]
    event = "push"

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

    gh_client = GitHubClient(installation_id, payload["installation"]["app_slug"], get_token_manager())
    compare_url = f"https://api.github.com/repos/{repo_full_name}/compare/{before}...{after}"

    response = gh_client.get(compare_url)
    if not response:
        logger.error("GitHub compare API failed (%s): %s", response.status_code, compare_url)
        return JsonResponse({"error": "GitHub API error"}, status=response.status_code)

    compare_data = response.json()
    changed_files = []
    for file in compare_data["files"]:
        entry = {"path": file["filename"], "status": file["status"]}
        if file["status"] == "renamed":
            entry["previous_path"] = file.get("previous_filename")
        changed_files.append(entry)

    q_process_changed_files(changed_files, repo_full_name, repo_data["id"], gh_client)
    logger.info(
        "Push event processed for %s (repo_id=%s): %d files changed by %s",
        repo_full_name,
        repo_data["id"],
        len(changed_files),
        sender_login,
    )

    return JsonResponse({"success": "Processed push event successfully"})


def handle_pull_request_event(payload: Dict[str, Any]) -> JsonResponse:
    validate(payload, PR_SCHEMA)

    action = payload["action"]
    installation_data = payload["installation"]
    installation_id = installation_data["id"]
    repo_data = payload["repository"]
    sender_login = payload["sender"]["login"]
    event = "pull_request"

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

    gh_client = GitHubClient(installation_id, installation_data["app_slug"], get_token_manager())

    pr_instance = PullRequest(payload)

    if action in {"opened", "reopened", "synchronize"}:  # TODO: Remove reopened onc dev testing done
        logger.info("Processing PR event: %r", pr_instance)
        if not pr_instance._verify_branch():
            logger.info("Skipping AI review due to branch mismatch for: %r", pr_instance)
            return JsonResponse({"error": f"Skipping AI review due to branch mismatch for PR  {pr_instance.number}"})

        pr_diff = gh_client.fetch_pr_diff(pr_instance.diff_url)
        processed_diff, patch = process_diff(pr_diff)

        diff_query = generate_diff_query(processed_diff)
        cleaned_json = extract_json_block(diff_query)
        diff_query_json = json.loads(cleaned_json)

        q = diff_query_json["quer"]
        key_terms = diff_query_json["key_terms"]
        k = diff_query_json["k"]

        combined_query = q + key_terms
        vector_query = generate_embedding(combined_query, EmbeddingTaskType.RETRIEVAL_QUERY)

        snippets: List[ChunkType] = []
        analysis_output: str = ""

        if not vector_query:
            logger.warning("Embedding generation failed for query: %s", combined_query)
        else:
            source_collection, temp_collection = create_temp_pr_collection(pr_instance, patch, gh_client)
            logger.info("Temporary collection created: %s", temp_collection)

            rename_mappings = {}
            for file in patch:
                rename_mappings[file.source_file] = file.target_file

            if source_collection and temp_collection:
                similar_chunks = q_get_similar_merged_chunks(
                    source_collection, temp_collection, vector_query, k, rename_mappings
                )
                snippets = format_chunks_to_string(similar_chunks)
                analysis_output = analyze_code_ruff_bandit(similar_chunks)
            else:
                logger.warning("Missing collection names: source=%s, temp=%s", source_collection, temp_collection)

        NOT_PROVIDED = "Not provided"
        prompt = PR_REVIEWER.format(
            pr_title=pr_instance.title or NOT_PROVIDED,
            pr_body=pr_instance.body or NOT_PROVIDED,
            pr_diff=processed_diff or NOT_PROVIDED,
            static_analysis_output=analysis_output or NOT_PROVIDED,
            relevant_snippets=snippets or NOT_PROVIDED,
        )

        bot_response_raw = generate_gemini_response(prompt)
        bot_response = bot_response_raw.get("text", "") if bot_response_raw else ""

        if not bot_response:
            logger.error(
                "Failed to generate AI review response for new PR: %s created in %s",
                pr_instance.title,
                pr_instance.repo_full_name,
            )
            return

        ai_response = f"{pr_analysis_marker()}\n{bot_response}"

        gh_comment = gh_client.post_comment(pr_instance.comments_url, bot_response)
        if not gh_comment:
            logger.error("Failed to post GitHub comment for PR #%s", pr_instance.number)
            return

        issue_data_for_comment = payload.get("pull_request", {})
        gh_comment = gh_comment.json()
        AibotComment.objects.create(
            installation=installation,
            repository=repo,
            issue_number=pr_instance.number,
            comment_id=gh_comment["id"],
            comment_url=gh_comment["html_url"],
            trigger_event=f"pull_request.{action}",
            triggered_by_username=issue_data_for_comment["user"]["login"],
            trigger_comment_body=issue_data_for_comment.get("body") or "",
            prompt=prompt,
            response=ai_response,
            model_used=(
                bot_response_raw.get("model", settings.GEMINI_GENERATION_MODEL)
                if bot_response_raw
                else settings.GEMINI_GENERATION_MODEL
            ),
            prompt_tokens=(
                bot_response_raw.get("prompt_tokens", approximate_token_count_char(prompt))
                if bot_response_raw
                else approximate_token_count_char(prompt)
            ),
            completion_tokens=(
                bot_response_raw.get("completion_tokens", approximate_token_count_char(bot_response))
                if bot_response_raw
                else approximate_token_count_char(bot_response)
            ),
        )
        logger.info("Completed review for %r", pr_instance)
    elif action == "closed":
        logger.debug("PR was closed: %r", pr_instance)
    return JsonResponse({"status": "PR event processed"})


def handle_issue_comment_event(payload: Dict[str, Any]) -> None:
    validate(payload, ISSUE_COMMENT_SCHEMA)

    installation_id = payload["installation"]["id"]
    repo_data = payload["repository"]
    sender_login = payload["sender"]["login"]

    if sender_login == f"{settings.GITHUB_AIBOT_APP_NAME}[bot]":
        logger.debug("This event is by blt-aibot's comment. Ignoring")
        return JsonResponse({"status": "Ignoring blt-aibot's own comment"})

    action = payload["action"]
    issue = payload["issue"]
    issue_type = "Pull request" if issue.get("pull_request") else "Issue"
    issue_body = issue["body"]
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

    comment_body = payload["comment"]["body"]
    bot_name = settings.GITHUB_AIBOT_APP_NAME.lower()
    mention_string = f"@{bot_name}"
    if mention_string not in comment_body:
        logger.debug("%s was not mentioned in comment. Ignoring", bot_name)
        return JsonResponse({"status": f"{bot_name} was not mentioned in comment. Ignoring"})

    gh_client = GitHubClient(installation_id, settings.GITHUB_AIBOT_APP_NAME, get_token_manager())

    comments_url = issue["comments_url"]
    if action == "created":
        comments = gh_client.get(comments_url)
        comments = comments.json()

        conversation_parts = []
        conversation_parts.append(f"[ISSUE by {issue['user']['login']}]: {issue['title']}\n{issue['body'] or ''}")

        for comment in comments:
            author = comment["user"]["login"]
            body = comment["body"]
            conversation_parts.append(f"[COMMENT by {author}]: {body}")

        conversation = "\n".join(conversation_parts)

        response = generate_conversation_query(conversation)
        logger.debug("Recieved conv query response: %s", response)
        conversation_cleaned_json = extract_json_block(response["text"])
        conversation_query_json = json.loads(conversation_cleaned_json)
        query = conversation_query_json["query"]
        k = conversation_query_json["k"]

        vector_query = generate_embedding(query, EmbeddingTaskType.RETRIEVAL_QUERY)

        semantically_relevant_chunks: ChunkType = q_get_similar_chunks(
            q_get_collection_name(repo.full_name, repo.repo_id), vector_query, k
        )

        snippets = format_chunks_to_string(semantically_relevant_chunks)

        prompt = ISSUE_COMMENT_RESPONDER.format(
            issue_type=issue_type,
            issue_title=issue["title"],
            issue_body=issue_body,
            conversation=conversation,
            relevant_snippets=snippets,
        )

        logger.debug("Built prompt: \n %s", prompt)
        bot_response_raw = generate_gemini_response(prompt)

        if not bot_response_raw:
            logger.error("Did not receive a valid LLM response for issue #%s", issue["number"])
            return JsonResponse({"error": "Did not receive a valid LLM response"}, status=500)

        ai_response_body = bot_response_raw["text"]
        gh_comment = gh_client.post_comment(comments_url, ai_response_body)

        if not gh_comment:
            logger.error("Failed to post/patch GitHub comment for issue #%s", issue["number"])
            return JsonResponse({"error": "Failed to post GitHub comment"}, status=500)

        gh_comment = gh_comment.json()
        logger.info("Posted AI response to issue #%s in %s", issue["number"], repo.full_name)

        AibotComment.objects.create(
            installation=installation,
            repository=repo,
            issue_number=issue["number"],
            comment_id=gh_comment["id"],
            comment_url=gh_comment["html_url"],
            trigger_event="issue_comment",
            triggered_by_username=sender_login,
            trigger_comment_body=issue_body,
            prompt=prompt,
            response=ai_response_body,
            model_used=(
                bot_response_raw.get("model", settings.GEMINI_GENERATION_MODEL)
                if bot_response_raw
                else settings.GEMINI_GENERATION_MODEL
            ),
            prompt_tokens=(
                bot_response_raw.get("prompt_tokens", approximate_token_count_char(prompt))
                if bot_response_raw
                else approximate_token_count_char(prompt)
            ),
            completion_tokens=(
                bot_response_raw.get("completion_tokens", approximate_token_count_char(ai_response_body))
                if bot_response_raw
                else approximate_token_count_char(ai_response_body)
            ),
        )

    else:
        logger.debug("Ignoring issue event with action=%s", action)
    return JsonResponse({"status": "Processed issue comment event"})


def handle_issues_event(payload: Dict[str, Any]) -> JsonResponse:
    validate(payload, ISSUE_SCHEMA)

    installation_data = payload["installation"]
    installation_id = installation_data["id"]
    repo_data = payload["repository"]
    sender_login = payload["sender"]["login"]
    action = payload["action"]
    issue_data = payload["issue"]
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
        issue_data["body"] = issue_data.get("body") or ""

        response = generate_issue_query(issue_data)
        logger.debug("Received issue query response: \n %s", response)
        issue_cleaned_json = extract_json_block(response["text"])
        issue_query_json = json.loads(issue_cleaned_json)
        query = issue_query_json["query"]
        k = issue_query_json["k"]

        vector_query = generate_embedding(query, EmbeddingTaskType.RETRIEVAL_QUERY)
        semantically_relevant_chunks: ChunkType = q_get_similar_chunks(
            q_get_collection_name(repo.full_name, repo.repo_id), vector_query, k
        )

        snippets = format_chunks_to_string(semantically_relevant_chunks)

        prompt = ISSUE_PLANNER.format(
            issue_title=issue_data["title"],
            issue_body=issue_data["body"] or "Not provided",
            code_chunks=snippets or "Not provided",
        )

        ai_response = generate_gemini_response(prompt)
        if not ai_response:
            logger.error("Did not receive a valid LLM response for issue #%s", issue_data["number"])
            return JsonResponse({"error": "Did not receive a valid LLM response"}, status=500)

        ai_response_body = ai_response["text"]
        final_text = issue_analysis_marker() + ai_response_body

        comments_url = issue_data["comments_url"]
        gh_client = GitHubClient(installation_id, installation_data["app_slug"], get_token_manager())
        if action == "opened":
            gh_comment = gh_client.post_comment(comments_url, final_text)
        else:
            gh_comment = gh_client.patch_comment(comments_url, final_text, issue_analysis_marker())

        if not gh_comment:
            logger.error("Failed to post/patch GitHub comment for issue #%s", issue_data["number"])
            return JsonResponse({"error": "Failed to post GitHub comment"}, status=500)

        gh_comment = gh_comment.json()
        logger.info("Posted AI response to issue #%s in %s", issue_data["number"], repo.full_name)

        AibotComment.objects.create(
            installation=installation,
            repository=repo,
            issue_number=issue_data["number"],
            comment_id=gh_comment["id"],
            comment_url=gh_comment["html_url"],
            trigger_event=f"issues.{action}",
            triggered_by_username=issue_data["user"]["login"],
            trigger_comment_body=issue_data.get("body") or "",
            prompt=prompt,
            response=final_text,
            model_used=ai_response["model"],
            prompt_tokens=ai_response["prompt_tokens"] or approximate_token_count_char(prompt),
            completion_tokens=ai_response["completion_tokens"] or approximate_token_count_char(ai_response_body),
        )
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
    logger.debug("Received payload: %s", json.dumps(payload, indent=2, sort_keys=True))

    signature_header = request.headers.get("X-Hub-Signature-256")
    webhook_secret = settings.GITHUB_AIBOT_WEBHOOK_SECRET
    valid_sig, err_sig = verify_github_signature(webhook_secret, request.body, signature_header)
    if not valid_sig:
        logger.error("Error in validating github request: %s", err_sig)
        return JsonResponse({"error": err_sig})

    handler = get_handler(event_type)
    if handler:
        return handler(payload)
    else:
        logger.error("No handler found for event type %s", event_type)
        return JsonResponse({"error": f"Unsupported event type {event_type}"})


def process_repository(
    repo_data: Dict[str, Any], installation: GithubAppInstallation, gh_client: GitHubClient
) -> Tuple[str | None, str | None]:
    repo_obj, _ = GithubAppRepo.objects.update_or_create(
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

    try:
        q_process_remote_repo(
            repo_obj.full_name,
            repo_obj.repo_id,
            gh_client,
            repo_obj.default_branch,
        )
        repo_obj.state = RepoState.ACTIVE
        repo_obj.save()
        return repo_obj.full_name, None
    except Exception as e:
        logger.error("Failed to process repo %s: failed to process repository", repo_obj.full_name, exc_info=True)
        repo_obj.state = RepoState.ERROR
        repo_obj.save()
        return None, repo_obj.full_name


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
    old_name = repo.full_name
    repo.name = repo_data["name"]
    repo.full_name = repo_data["full_name"]
    repo.save()

    try:
        rename_qdrant_collection_with_alias(old_name, repo_data["full_name"])
        logger.info("Renamed Qdrant collection from '%s' to '%s' using alias.", old_name, repo_data["full_name"])
    except ValueError as e:
        logger.error("Failed to rename Qdrant collection: %s", e)
    except Exception as e:
        logger.error("Unexpected error renaming Qdrant collection: %s", e)

    logger.info(
        "Renamed repository from %s to %s (id=%s) by sender=%s",
        old_name,
        repo.full_name,
        repo.repo_id,
        sender_login,
    )
    return


def ensure_repo_entry(
    repo_data: Dict[str, Any], installation: GithubAppInstallation, gh_client: GitHubClient
) -> Tuple[GithubAppRepo, bool]:
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

    collection_name = q_get_collection_name(repo_data["full_name"], repo_data["id"])
    if created or not q_collection_exists(collection_name):
        logger.info("Repo collection for %s not found. Processing now.", repo_data["full_name"])
        q_process_remote_repo(repo_data["full_name"], repo_data["id"], gh_client)

    return repo_obj, created


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
    return JsonResponse({"success": "App state modified successfully."})


def handle_repo_state_change(repo: GithubAppRepo, action: str, sender_login: str) -> None:
    if REPO_STATE_CHANGES[action]:
        repo.state = REPO_STATE_CHANGES[action]
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
    return


def generate_diff_query(processed_diff: str) -> str:
    prompt = PR_QUERY_GENERATOR.format(diff=processed_diff)
    response = generate_gemini_response(prompt)
    return response


def generate_issue_query(issue_content: str) -> List[float]:
    prompt = ISSUE_QUERY.format(issue_title=issue_content["title"], issue_body=issue_content["body"])
    response = generate_gemini_response(prompt)
    return response


def generate_conversation_query(conversation: str) -> List[float]:
    prompt = CONVERSATION_QUERY_GENERATOR.format(conversation=conversation)
    response = generate_gemini_response(prompt)
    return response
