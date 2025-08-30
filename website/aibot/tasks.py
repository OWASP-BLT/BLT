import json
import logging
from typing import Any, Dict, List, Tuple

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from website.aibot.gemini_api import generate_embedding, generate_gemini_response
from website.aibot.gh_token_manager import get_token_manager
from website.aibot.github_api import GitHubClient
from website.aibot.models import PullRequest
from website.aibot.prompt_templates import (
    CONVERSATION_QUERY_GENERATOR,
    GUARDRAIL,
    ISSUE_COMMENT_RESPONDER,
    ISSUE_PLANNER,
    ISSUE_QUERY,
    PR_QUERY_GENERATOR,
    PR_REVIEWER,
)
from website.aibot.qdrant_api import (
    q_create_temp_pr_collection,
    q_delete_collection,
    q_get_collection_name,
    q_get_similar_chunks,
    q_get_similar_merged_chunks,
    q_process_changed_files,
    q_process_remote_repo,
)
from website.aibot.types import ChunkType, EmbeddingTaskType
from website.aibot.utils import (
    analyze_code_ruff_bandit,
    approximate_token_count_char,
    extract_json_block,
    format_chunks_to_string,
    issue_analysis_marker,
    pr_analysis_marker,
    process_diff,
)
from website.models import AibotComment, GithubAppInstallation, GithubAppRepo, RepoState

logger = logging.getLogger(__name__)

APP_NAME = settings.GITHUB_AIBOT_APP_NAME


@shared_task
def process_repos_added_task(installation_id: str, repos_added: List[Dict]) -> None:
    processed_repos, failed_repos = [], []
    installation = GithubAppInstallation.objects.get(installation_id=installation_id)
    gh_client = GitHubClient(installation_id, APP_NAME, get_token_manager())
    for repo_data in repos_added:
        repo_obj, _ = upsert_repo_db(repo_data, installation)
        try:
            q_process_remote_repo(
                repo_obj.full_name,
                repo_obj.repo_id,
                gh_client,
                repo_obj.default_branch,
            )
            repo_obj.state = RepoState.ACTIVE
            processed_repos.append(repo_obj)
        except Exception:
            logger.error("Failed to process repo %s", repo_obj.full_name, exc_info=True)
            repo_obj.state = RepoState.ERROR
            failed_repos.append(repo_obj)
        repo_obj.save()

    logger.info(
        "Repository processing completed for installation_id=%s: %d succeeded, %d failed. Successful: %s | Failed: %s",
        installation_id,
        len(processed_repos),
        len(failed_repos),
        [r.name for r in processed_repos],
        [r.name for r in failed_repos],
    )
    return


@shared_task
def process_repos_removed_task(installation_id: str, repos_removed: List[Dict]) -> None:
    removed_repos, failed_repos = [], []
    installation = GithubAppInstallation.objects.get(installation_id=installation_id)

    for repo_data in repos_removed:
        repo_id = repo_data["id"]
        full_name = repo_data["full_name"]

        GithubAppRepo.objects.filter(installation=installation, repo_id=repo_id).update(
            state=RepoState.REMOVED, updated_at=timezone.now()
        )

        try:
            q_delete_collection(q_get_collection_name(full_name, repo_id))
            removed_repos.append(repo_data)
        except Exception:
            logger.error("Failed to delete collection for repo %s", full_name, exc_info=True)
            failed_repos.append(repo_data)

    logger.info(
        "Repository removal completed for installation_id=%s: %d succeeded, %d failed for app_name=%s. Successful: %s | Failed: %s",
        installation_id,
        len(removed_repos),
        len(failed_repos),
        APP_NAME,
        [r["full_name"] for r in removed_repos],
        [r["full_name"] for r in failed_repos],
    )
    return


@shared_task
def process_push_task(
    installation_id: str, repo_id: str, repo_full_name: str, base_commit_sha: str, head_commit_sha: str
) -> None:
    gh_client = GitHubClient(installation_id, APP_NAME, get_token_manager())
    compare_url = f"https://api.github.com/repos/{repo_full_name}/compare/{base_commit_sha}...{head_commit_sha}"
    response = gh_client.get(compare_url)
    if not response:
        logger.error("GitHub compare API failed (%s): %s", response.status_code, compare_url)

    compare_data = response.json()
    changed_files = []
    for file in compare_data["files"]:
        entry = {"path": file["filename"], "status": file["status"]}
        if file["status"] == "renamed":
            entry["previous_path"] = file.get("previous_filename")
        changed_files.append(entry)

    q_process_changed_files(changed_files, repo_full_name, repo_id, gh_client)
    logger.info(
        "Push event processed for installation_id=%s repo %s (id=%s): %d files changed.",
        installation_id,
        repo_full_name,
        repo_id,
        len(changed_files),
    )
    return


@shared_task
def process_pr_task(installation_id: str, repo_id: str, action: str, payload: Dict[str, Any]) -> None:
    installation = GithubAppInstallation.objects.get(installation_id=installation_id)
    repo = GithubAppRepo.objects.get(repo_id=repo_id)
    pr_instance = PullRequest(payload)
    logger.info("Processing PR event for installation_id=%s: \n %r", installation_id, pr_instance)

    if not pr_instance._verify_branch():
        logger.error("Skipping AI review due to branch mismatch for PR %r", pr_instance)
        return

    gh_client = GitHubClient(installation_id, APP_NAME, get_token_manager())

    pr_diff = gh_client.fetch_pr_diff(pr_instance.diff_url)
    processed_diff, patch = process_diff(pr_diff)

    response = generate_diff_query(processed_diff)
    logger.debug("Received diff query response: %s", response)

    cleaned_json = extract_json_block(response["text"])
    diff_query_json = json.loads(cleaned_json)

    q = diff_query_json["query"]
    key_terms = diff_query_json["key_terms"]
    k = diff_query_json["k"]

    combined_query = q + key_terms
    vector_query = generate_embedding(combined_query, EmbeddingTaskType.RETRIEVAL_QUERY)

    snippets: List[ChunkType] = []
    analysis_output: str = ""

    if not vector_query:
        logger.warning("Embedding generation failed for query: %s", combined_query)
    else:
        source_collection, temp_collection = q_create_temp_pr_collection(pr_instance, patch, gh_client)
        logger.info("Temporary collection created: %s", temp_collection)

        rename_mappings = {}
        for file in patch:
            rename_mappings[file.source_file] = file.target_file

        if source_collection and temp_collection:
            similar_chunks = q_get_similar_merged_chunks(
                source_collection, temp_collection, vector_query, k, rename_mappings
            )
            snippets = format_chunks_to_string(similar_chunks)
            py_chunks = [chunk for chunk in similar_chunks if chunk["file_ext"] == ".py"]
            analysis_output = analyze_code_ruff_bandit(py_chunks)
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

    prompt_with_guardrail = f"{GUARDRAIL} \n {prompt}"

    logger.debug("Full prompt for review: \n %s", prompt_with_guardrail)

    bot_response_raw = generate_gemini_response(prompt_with_guardrail)
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

    q_delete_collection(temp_collection)

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
        prompt=prompt_with_guardrail,
        response=ai_response,
        model_used=(
            bot_response_raw.get("model", settings.GEMINI_GENERATION_MODEL)
            if bot_response_raw
            else settings.GEMINI_GENERATION_MODEL
        ),
        prompt_tokens=(
            bot_response_raw.get("prompt_tokens", approximate_token_count_char(prompt_with_guardrail))
            if bot_response_raw
            else approximate_token_count_char(prompt_with_guardrail)
        ),
        completion_tokens=(
            bot_response_raw.get("completion_tokens", approximate_token_count_char(bot_response))
            if bot_response_raw
            else approximate_token_count_char(bot_response)
        ),
    )
    logger.info("Completed review for %r", pr_instance)

    return


@shared_task
def process_issue_comment_task(installation_id: str, repo_id: str, issue: Dict[str, Any], sender_login: str) -> None:
    installation = GithubAppInstallation.objects.get(installation_id=installation_id)
    repo = GithubAppRepo.objects.get(repo_id=repo_id)
    gh_client = GitHubClient(installation_id, APP_NAME, get_token_manager())
    issue_type = "Pull request" if issue.get("pull_request") else "Issue"
    issue_body = issue["body"]
    comments_url = issue["comments_url"]
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

    prompt_with_guardrail = f"{GUARDRAIL} \n {prompt}"

    logger.debug("Built prompt: \n %s", prompt_with_guardrail)
    bot_response_raw = generate_gemini_response(prompt_with_guardrail)

    if not bot_response_raw:
        logger.error("Did not receive a valid LLM response for issue #%s", issue["number"])
        return

    ai_response_body = bot_response_raw["text"]
    gh_comment = gh_client.post_comment(comments_url, ai_response_body)

    if not gh_comment:
        logger.error("Failed to post/patch GitHub comment for issue #%s", issue["number"])
        return

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
        prompt=prompt_with_guardrail,
        response=ai_response_body,
        model_used=(
            bot_response_raw.get("model", settings.GEMINI_GENERATION_MODEL)
            if bot_response_raw
            else settings.GEMINI_GENERATION_MODEL
        ),
        prompt_tokens=(
            bot_response_raw.get("prompt_tokens", approximate_token_count_char(prompt_with_guardrail))
            if bot_response_raw
            else approximate_token_count_char(prompt_with_guardrail)
        ),
        completion_tokens=(
            bot_response_raw.get("completion_tokens", approximate_token_count_char(ai_response_body))
            if bot_response_raw
            else approximate_token_count_char(ai_response_body)
        ),
    )
    return


@shared_task
def process_issue_task(
    installation_id: str, repo_id: str, action: str, issue: Dict[str, Any], sender_login: str
) -> None:
    installation = GithubAppInstallation.objects.get(installation_id=installation_id)
    repo = GithubAppRepo.objects.get(repo_id=repo_id)
    gh_client = GitHubClient(installation_id, APP_NAME, get_token_manager())

    issue_body = issue.get("body") or ""
    response = generate_issue_query(issue)
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
        issue_title=issue["title"],
        issue_body=issue["body"] or "Not provided",
        code_chunks=snippets or "Not provided",
    )

    prompt_with_guardrail = f"{GUARDRAIL} \n {prompt}"

    ai_response = generate_gemini_response(prompt_with_guardrail)
    if not ai_response:
        logger.error("Did not receive a valid LLM response for issue #%s", issue["number"])
        return

    ai_response_body = ai_response["text"]
    final_text = issue_analysis_marker() + ai_response_body

    comments_url = issue["comments_url"]
    gh_client = GitHubClient(installation_id, APP_NAME, get_token_manager())
    if action == "opened":
        gh_comment = gh_client.post_comment(comments_url, final_text)
    else:
        gh_comment = gh_client.patch_comment(comments_url, final_text, issue_analysis_marker())

    if not gh_comment:
        logger.error("Failed to post/patch GitHub comment for issue #%s", issue["number"])
        return

    gh_comment = gh_comment.json()
    logger.info("Posted AI response to issue #%s in %s", issue["number"], repo.full_name)

    AibotComment.objects.create(
        installation=installation,
        repository=repo,
        issue_number=issue["number"],
        comment_id=gh_comment["id"],
        comment_url=gh_comment["html_url"],
        trigger_event=f"issues.{action}",
        triggered_by_username=sender_login,
        trigger_comment_body=issue_body,
        prompt=prompt_with_guardrail,
        response=final_text,
        model_used=ai_response["model"],
        prompt_tokens=ai_response["prompt_tokens"] or approximate_token_count_char(prompt_with_guardrail),
        completion_tokens=ai_response["completion_tokens"] or approximate_token_count_char(ai_response_body),
    )
    return


def upsert_repo_db(repo_data: Dict[str, Any], installation: GithubAppInstallation) -> Tuple[GithubAppRepo, bool]:
    """Lightweight ORM helper, no heavy work here."""
    return GithubAppRepo.objects.update_or_create(
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
