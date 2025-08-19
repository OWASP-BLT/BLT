"""This module handles the GitHub AI Bot webhook events and interactions.
It processes pull requests, issues, and comments, and interacts with the
Gemini AI API to generate responses and post them on github.
"""

import json
import logging
from typing import Any, Dict, List

import requests
from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST
from jsonschema import ValidationError, validate

from website.aibot.aibot_env import configure_and_validate_settings, load_prompts, load_validation_schemas
from website.aibot.clients import q_client
from website.aibot.models import PullRequest
from website.aibot.network import (
    fetch_pr_diff,
    generate_embedding,
    generate_gemini_response,
    github_api_get,
    patch_github_comment,
    post_github_comment,
)
from website.aibot.qdrant_utils import (
    create_temp_pr_collection,
    q_collection_exists,
    q_get_collection_name,
    q_get_similar_chunks,
    q_get_similar_merged_chunks,
    q_process_changed_files,
    q_process_remote_repote_repo,
    rename_qdrant_collection_with_alias,
)
from website.aibot.utils import (
    analyze_code_ruff_bandit,
    approximate_token_count_char,
    extract_json_block,
    format_chunks_to_string,
    issue_analysis_marker,
    parse_json,
    pr_analysis_marker,
    process_diff,
    sign_payload,
    validate_github_request,
    verify_github_signature,
)
from website.models import AibotComment, GithubAppInstallation, GithubAppRepo, InstallationState, RepoState

logger = logging.getLogger(__name__)

configure_and_validate_settings()


SCHEMAS = load_validation_schemas()
PROMPTS = load_prompts()


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
    action = payload["action"]
    installation_data = payload["installation"]
    account_data = installation_data["account"]
    sender_login = payload.get("sender", {}).get("login")

    if action == "created":
        installation, _ = GithubAppInstallation.objects.get_or_create(
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
        failed_repos = []

        for repo_data in payload.get("repositories", []):
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
                q_process_remote_repote_repo(q_client, repo_obj.full_name, repo_obj.repo_id, repo_obj.default_branch)
                repo_obj.state = RepoState.READY
                repo_obj.save(update_fields=["state"])
                processed_repos.append(repo_obj.full_name)
            except Exception as e:
                logger.error("Failed to process repo %s: %s", repo_obj.full_name, e, exc_info=True)
                repo_obj.state = RepoState.ERROR
                repo_obj.save(update_fields=["state"])
                failed_repos.append(repo_obj.full_name)

        return JsonResponse(
            {
                "success": True,
                "processed_repos": processed_repos,
                "failed_repos": failed_repos,
            }
        )

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

        collection_name = q_get_collection_name(repo_data["full_name"], repo_data["id"])

        if created or not q_collection_exists(q_client, collection_name):
            logger.info("Repo collection for %s not found. Processing now.", repo_data["full_name"])
            q_process_remote_repote_repo(q_client, repo_data["full_name"], repo_data["id"])

        processed_repos.append((repo_obj.full_name, created))

    created_repos = [name for name, created in processed_repos if created]
    updated_repos = [name for name, created in processed_repos if not created]

    if processed_repos:
        logger.info(
            "Processed %d repositories for installation_id=%s. Created: %d, Updated: %d. Repos: %s",
            len(processed_repos),
            installation_id,
            len(created_repos),
            len(updated_repos),
            [name for name, _ in processed_repos],
        )

    # TODO: Create jobs to routinely remove stale repositories from qdrant
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

        try:
            rename_qdrant_collection_with_alias(q_client, old_name, repo.full_name)
            logger.info("Renamed Qdrant collection from '%s' to '%s' using alias.", old_name, repo.full_name)
        except ValueError as e:
            logger.error("Failed to rename Qdrant collection: %s", str(e))
        except Exception as e:
            logger.error("Unexpected error while renaming Qdrant collection: %s", str(e))

        logger.info(
            "Renamed repository from %s to %s (id=%s) by sender=%s",
            old_name,
            repo.full_name,
            repo.repo_id,
            sender_login,
        )

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


def handle_push_event(payload: Dict[str, Any]) -> JsonResponse:
    # TODO: Add payload validation for required fields
    repo_full_name = payload["repository"]["full_name"]
    repo_id = payload["repository"]["id"]
    before = payload["before"]
    after = payload["after"]

    compare_url = f"https://api.github.com/repos/{repo_full_name}/compare/{before}...{after}"

    compare_data = github_api_get(compare_url)
    if not compare_data:
        logger.error("Failed to fetch compare data via %s", compare_url)
        return JsonResponse({"error": "Failed to fetch compare data"}, status=500)

    changed_files = []
    for file in compare_data.get("files", []):
        entry = {"path": file["filename"], "status": file["status"]}
        if file["status"] == "renamed":
            entry["previous_path"] = file.get("previous_filename")
        changed_files.append(entry)

    q_process_changed_files(q_client, changed_files, repo_full_name, repo_id)

    return JsonResponse({"success": "Processed push event successfully"})


def handle_ping(payload: Dict[str, Any]) -> JsonResponse:
    zen = payload.get("zen", "No zen message received.")
    logger.info("Webhook ping received: %s", zen)
    return JsonResponse({"status": "pong", "zen": zen}, status=200)


def handle_pull_request_event(payload: Dict[str, Any]) -> JsonResponse:
    validate_payload_schema(payload, {})

    pr_instance = PullRequest(payload)
    action = pr_instance.action

    if action in ("opened", "reopened", "synchronize"):  # TODO: Remove reopened onc dev testing done
        logger.info("Processing PR event: %r", pr_instance)
        if pr_instance._verify_branch():
            pr_diff = fetch_pr_diff(pr_instance.diff_url)
            processed_diff, patch = process_diff(pr_diff)
            diff_query = generate_diff_query(processed_diff)
            cleaned_json = extract_json_block(diff_query)
            diff_query_json = json.loads(cleaned_json)

            q = diff_query_json.get("query")
            key_terms = diff_query_json.get("key_terms")
            k = diff_query_json.get("k")

            combined_query = q + key_terms
            vector_query = generate_embedding(combined_query)

            snippets = None
            analysis_output = None

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
                    similar_chunks = q_get_similar_merged_chunks(
                        None, source_collection, temp_collection, vector_query, k, rename_mappings
                    )
                    snippets = format_chunks_to_string(similar_chunks)
                    analysis_output = analyze_code_ruff_bandit(similar_chunks)
                else:
                    logger.warning("Missing collection names: source=%s, temp=%s", source_collection, temp_collection)

            prompt = PROMPTS["PR_REVIEWER"].format(
                pr_title=pr_instance.title or not_provided,
                pr_body=pr_instance.body or not_provided,
                pr_diff=processed_diff or not_provided,
                static_analysis_output=analysis_output or not_provided,
                relevant_snippets=snippets or not_provided,
            )
            not_provided = "Not provided"

            bot_response_raw = generate_gemini_response(prompt)
            bot_response = bot_response_raw.get("text", "")

            if not bot_response:
                logger.error(
                    "Failed to generate AI review response for new PR: %s created in %s",
                    pr_instance.title,
                    pr_instance.repo_full_name,
                )
            ai_response = f"{pr_analysis_marker()}\n{bot_response}"

            gh_comment = post_github_comment(pr_instance.comments_url, bot_response)

            installation_data = payload.get("installation", {})
            repository_data = payload.get("repository", {})
            issue_data_for_comment = payload.get("pull_request", {})

            AibotComment.objects.create(
                installation=installation_data,
                repository=repository_data,
                issue_number=pr_instance.number,
                comment_id=gh_comment["id"],
                comment_url=gh_comment["html_url"],
                trigger_event=f"issues.{action}",
                triggered_by_username=issue_data_for_comment["user"]["login"],
                trigger_comment_body=issue_data_for_comment.get("body") or "",
                prompt=prompt,
                response=ai_response,
                model_used=bot_response_raw["model"],
                prompt_tokens=bot_response_raw["prompt_tokens"] or approximate_token_count_char(prompt),
                completion_tokens=bot_response_raw["completion_tokens"] or approximate_token_count_char(bot_response),
            )

            if not gh_comment:
                logger.error("Failed to post github comment to URL: %s", pr_instance.comments_url)
            else:
                logger.info("Completed review for %r", pr_instance)
        else:
            logger.info("Skipping AI review due to branch mismatch for: %r", pr_instance)
    elif action == "closed":
        logger.debug("PR closed: %r", pr_instance)
    return JsonResponse({"status": "PR event processed"})


def handle_issue_comment_event(payload: Dict[str, Any]) -> None:
    validate_payload_schema(payload, SCHEMAS["COMMENT_SCHEMA"])
    logger.debug("Received issue comment event: \n %s", json.dumps(payload, indent=2))

    installation_id = payload["installation"]["id"]
    repo_data = payload["repository"]
    action = payload["action"]
    issue = payload["issue"]
    issue_body = issue["body"]

    bot_username = settings.GITHUB_AIBOT_USERNAME.lower()
    if bot_username not in issue_body:
        logger.debug("%s was not mentioned in comment. Ignoring", bot_username)
        return JsonResponse({"status": f"{bot_username} was not mentioned in comment. Ignoring"})

    issue_type = "Pull request" if issue.get("pull_request") else "Issue"
    comments_url = issue["comments_url"]
    if action == "created":
        # More advanced handling could also include another semantic code retreival from the conversaton,
        # however the blt bot's pr review comment has sufficient context for now
        logger.debug("Handling %s action with url: %s", action, issue["url"])
        try:
            installation = GithubAppInstallation.objects.get(installation_id=installation_id)
            installation_state = installation.state

            if installation_state != "active":
                logger.error(
                    "Received 'issues' event for installation id %s with invalid state: %s",
                    installation.installation_id,
                    installation_state,
                )
                return JsonResponse({"error": f"Invalid installation state: {installation_state}"})

            repo = GithubAppRepo.objects.get(installation=installation, repo_id=repo_data["id"])
            if repo.state != "active":
                return JsonResponse({"error": f"Invalid repo state: {repo.state}"})

            comments = github_api_get(comments_url)

            logger.debug("Processing for following comments: %s", json.dump(comments, indent=2))

            conversation_parts = []

            conversation_parts.append(f"[ISSUE by {issue['user']['login']}]: {issue['title']}\n{issue['body'] or ''}")

            for comment in comments:
                author = comment["user"]["login"]
                body = comment["body"]
                conversation_parts.append(f"[COMMENT by {author}]: {body}")

            conversation = "\n\n".join(conversation_parts)
            logger.debug("Built conversation:\n%s", conversation)

            prompt = PROMPTS["ISSUE_COMMENT_RESPONDER"].format(
                issue_type=issue_type, issue_title=issue["title"], issue_body=issue_body, conversation=conversation
            )

            ai_response = generate_gemini_response(prompt)

            if not ai_response:
                logger.error("Did not receive a valid LLM response for issue #%s", issue["number"])
                return JsonResponse({"error": "Did not receive a valid LLM response"}, status=500)

            ai_response_body = ai_response["text"]
            gh_comment = post_github_comment(comments_url, ai_response_body)

            if not gh_comment:
                logger.error("Failed to post/patch GitHub comment for issue #%s", issue["number"])
                return JsonResponse({"error": "Failed to post GitHub comment"}, status=500)

            logger.info("Posted AI response to issue #%s in %s", issue["number"], repo.full_name)

            AibotComment.objects.create(
                installation=installation,
                repository=repo,
                issue_number=issue["number"],
                comment_id=gh_comment["id"],
                comment_url=gh_comment["html_url"],
                trigger_event=f"issue_comment.{action}",
                triggered_by_username=issue["user"]["login"],
                trigger_comment_body=issue.get("body") or "",
                prompt=prompt,
                response=ai_response_body,
                model_used=ai_response["model"],
                prompt_tokens=ai_response["prompt_tokens"] or approximate_token_count_char(prompt),
                completion_tokens=ai_response["completion_tokens"] or approximate_token_count_char(ai_response_body),
            )

        except GithubAppInstallation.DoesNotExist:
            logger.error("Installation %s not found", installation_id)
            return JsonResponse({"error": "Installation not found"}, status=404)
        except GithubAppRepo.DoesNotExist:
            logger.error("Repo %s not found in db", repo_data["full_name"])
            return JsonResponse({"error": f"Repo not found: {repo_data['full_name']}"}, status=404)
    else:
        logger.debug("Ignoring issue event with action=%s", action)
    return


def handle_issues_event(payload: Dict[str, Any]) -> JsonResponse:
    logger.debug("Received payload of 'issues' event: \n %s", json.dumps(payload, indent=2))
    validate_payload_schema(payload, SCHEMAS["ISSUE_SCHEMA"])

    installation_id = payload["installation"]["id"]
    repo_data = payload["repository"]
    action = payload["action"]
    issue_data = payload["issue"]

    if action in {"opened", "edited"}:
        try:
            installation = GithubAppInstallation.objects.get(installation_id=installation_id)
            installation_state = installation.state
            if installation_state != "active":
                logger.error(
                    "Received 'issues' event for installation id %s with invalid state: %s",
                    installation.installation_id,
                    installation_state,
                )
                return JsonResponse({"error": f"Invalid installation state: {installation_state}"})

            repo = GithubAppRepo.objects.get(installation=installation, repo_id=repo_data["id"])
            if repo.state != "active":
                return JsonResponse({"error": f"Invalid repo state: {repo.state}"})

            issue_data["body"] = issue_data.get("body") or ""

            issue_query = generate_issue_query(issue_data)
            issue_cleaned_json = extract_json_block(issue_query)
            issue_query_json = json.loads(issue_cleaned_json)
            query = issue_query_json.get("query")
            k = issue_query_json.get("k")

            semantically_relevant_chunks = q_get_similar_chunks(
                q_client, q_get_collection_name(repo.full_name, repo.repo_id), query, k
            )
            snippets = format_chunks_to_string(semantically_relevant_chunks)

            prompt = PROMPTS["ISSUE_PLANNER"].format(
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
            if action == "opened":
                gh_comment = post_github_comment(comments_url, final_text)
            else:
                gh_comment = patch_github_comment(comments_url, final_text, issue_analysis_marker())

            if not gh_comment:
                logger.error("Failed to post/patch GitHub comment for issue #%s", issue_data["number"])
                return JsonResponse({"error": "Failed to post GitHub comment"}, status=500)

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

        except GithubAppInstallation.DoesNotExist:
            logger.error("Installation %s not found", installation_id)
            return JsonResponse({"error": "Installation not found"}, status=404)
        except GithubAppRepo.DoesNotExist:
            logger.error("Repo %s not found in db", repo_data["full_name"])
            return JsonResponse({"error": f"Repo not found: {repo_data['full_name']}"}, status=404)
    else:
        logger.debug("Ignoring issue event with action=%s", action)

    return JsonResponse({"success": "processed"})


EVENT_HANDLERS = {
    "ping": handle_ping,
    "pull_request": handle_pull_request_event,
    "issue_comment": handle_issue_comment_event,
    "issues": handle_issues_event,
    "installation": handle_installation_event,
    "installation_repositories": handle_installation_repositories_event,
    "repository": handle_repository_event,
    "push": handle_push_event,
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


def generate_diff_query(processed_diff: str) -> str:
    prompt = PROMPTS["SEMANTIC_QUERY_GENERATOR"].format(diff=processed_diff)
    response = generate_gemini_response(prompt)
    return response


def generate_issue_query(issue_content: str) -> List[float]:
    prompt = PROMPTS["ISSUE_QUERY"].format(issue_title=issue_content["title"], issue_body=issue_content["body"])
    response = generate_gemini_response(prompt)
    return response


def validate_payload_schema(payload: Dict[str, Any], schema: Dict[str, Any]) -> None:
    validate(instance=payload, schema=schema)
