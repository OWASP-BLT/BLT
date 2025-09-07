import json
import logging
import re
from typing import Any, Dict, List, Tuple

from django.conf import settings
from qdrant_client.http import models
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.http.models import UpdateStatus
from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct
from unidiff import PatchSet

from website.aibot.chunk_utils import chunk_file, postprocess_chunks
from website.aibot.clients import q_client
from website.aibot.constants import MAX_FILE_SIZE
from website.aibot.gemini_api import generate_embedding
from website.aibot.github_api import GitHubClient
from website.aibot.models import PullRequest
from website.aibot.types import ChunkType, EmbeddingTaskType
from website.aibot.utils import generate_chunk_uuid, sanitize_name, should_skip_file
from website.models import GithubAppInstallation, RepoState

logger = logging.getLogger(__name__)

QDRANT_VECTOR_SIZE = settings.QDRANT_VECTOR_SIZE


def ensure_collection(qdrant_collection: str, qdrant_vector_size: int) -> None:
    logger.debug("---------------- ENSURING COLLECTION %s -----------", qdrant_collection)
    try:
        q_client.create_collection(
            collection_name=qdrant_collection,
            vectors_config={"size": int(qdrant_vector_size), "distance": "Cosine"},
        )
        logger.info("Created Qdrant collection '%s'", qdrant_collection)
    except UnexpectedResponse as e:
        if "already exists" in str(e):
            logger.debug("Collection or alias '%s' already exists. Skipping creation.", qdrant_collection)
        else:
            logger.error("Failed to create Qdrant collection '%s'. Error: %s", qdrant_collection, str(e))
            raise


def q_delete_collection(qdrant_collection: str) -> bool:
    try:
        collections = [c.name for c in q_client.get_collections().collections]
        if qdrant_collection not in collections:
            logger.info("Collection '%s' does not exist", qdrant_collection)
            return False

        result = q_client.delete_collection(collection_name=qdrant_collection)

        if result is True or getattr(result, "status", None) == "ok":
            logger.info("Deleted collection '%s'", qdrant_collection)
            return True
        else:
            logger.error("Deletion of collection '%s' failed, response: %s", qdrant_collection, result)
            return False

    except Exception as e:
        logger.error("Error deleting collection '%s': %s", qdrant_collection, str(e))
        return False


def upsert_to_qdrant(qdrant_collection: str, chunk: ChunkType, embedding: List[float]) -> bool:
    """Upsert the embedding in the specified Qdrant collection."""
    point_id = generate_chunk_uuid(chunk)
    point = PointStruct(
        id=point_id,
        vector=embedding,
        payload={
            "file_path": chunk["file_path"],
            "file_name": chunk["file_name"],
            "file_ext": chunk.get("file_ext"),
            "chunk_type": chunk.get("chunk_type"),
            "content": chunk["content"],
            "start_line": chunk["start_line"],
            "end_line": chunk["end_line"],
            "part_index": chunk.get("part_index"),
            "part_total": chunk.get("part_total"),
        },
    )

    logger.debug(
        "Preparing upsert for point '%s' in collection '%s'. File: '%s', Chunk Type: '%s'",
        point_id,
        qdrant_collection,
        chunk.get("file_name"),
        chunk.get("chunk_type"),
    )

    try:
        result = q_client.upsert(
            collection_name=qdrant_collection,
            points=[point],
        )
        if result.status == UpdateStatus.COMPLETED:
            logger.info(
                "Successfully upserted point '%s' into collection '%s'. Operation ID: %s, Status: %s",
                point_id,
                qdrant_collection,
                result.operation_id,
                result.status.value,
            )
            return True
        else:
            logger.error(
                "Failed to upsert point '%s' into collection '%s'. Response: %s", point_id, qdrant_collection, result
            )
            return False

    except Exception as e:
        logger.error(
            "An unexpected error occurred during upsert of point '%s' into collection '%s': %s",
            point_id,
            qdrant_collection,
            e,
            exc_info=True,
        )
        return False


def q_create_temp_pr_collection(pr_instance: PullRequest, patch: PatchSet, gh_client: GitHubClient) -> Tuple[str, str]:
    source_collection = q_get_collection_name(pr_instance.repo_full_name, pr_instance.repo_id)
    sanitized_head_ref = sanitize_name(pr_instance.head_branch)
    temp_collection = f"temp_{sanitized_head_ref}_{pr_instance.number}"

    logger.debug("Ensuring source collection '%s' and temp collection '%s'", source_collection, temp_collection)
    ensure_collection(source_collection, QDRANT_VECTOR_SIZE)
    ensure_collection(temp_collection, QDRANT_VECTOR_SIZE)

    for file in patch:
        if not file.is_modified_file:
            continue

        fpath = file.source_file
        if file.is_rename:
            fpath = file.target_file
        fpath = fpath[2:]

        logger.debug("Processing file '%s' from patch", fpath)
        content = gh_client.fetch_file_content(pr_instance.repo_full_name, fpath, pr_instance.head_branch)

        if not content:
            logger.warning("No content fetched for file '%s'", fpath)
            continue

        chunks: List[ChunkType] = chunk_file(content, fpath)
        chunks = postprocess_chunks(chunks)
        logger.debug("Chunked file '%s' into %d chunks (postprocessed)", fpath, len(chunks))

        for chunk in chunks:
            try:
                embedding = generate_embedding(chunk["content"], EmbeddingTaskType.RETRIEVAL_DOCUMENT)
            except Exception as e:
                logger.error("Failed to generate embedding for chunk in file '%s': %s", fpath, str(e))
                continue

            if not embedding:
                logger.warning("No embedding generated for chunk in file '%s'", fpath)
                continue

            _ = upsert_to_qdrant(temp_collection, chunk, embedding)

    logger.debug("Finished creating temp collection '%s' for PR #%s", temp_collection, pr_instance.number)
    return source_collection, temp_collection


def q_get_similar_merged_chunks(
    source_collection: str,
    temp_collection: str,
    vector_query: str,
    k: int,
    rename_mappings: Dict[str, str],
) -> List[ChunkType]:
    main_points = q_client.query_points(collection_name=source_collection, query=vector_query, limit=k)
    temp_points = q_client.query_points(collection_name=temp_collection, query=vector_query, limit=k)

    relevant_chunks: List[ChunkType] = []

    pr_file_paths = set()
    for point in temp_points.points:
        chunk_data = point.payload
        file_path = chunk_data.get("file_path")
        renamed_path = rename_mappings.get(file_path, file_path)
        chunk_data["file_path"] = renamed_path
        pr_file_paths.add(renamed_path)
        relevant_chunks.append(chunk_data)

    for point in main_points.points:
        chunk_data = point.payload
        file_path = chunk_data.get("file_path")
        if file_path not in pr_file_paths:
            relevant_chunks.append(chunk_data)

    return relevant_chunks


def q_get_similar_chunks(
    collection: str,
    query: str,
    k: int,
) -> List[ChunkType]:
    logger.debug("Querying Qdrant collection '%s' for top %d similar chunks.", collection, k)

    result = q_client.query_points(collection_name=collection, query=query, limit=k)
    chunks = [point.payload for point in result.points]

    logger.debug("Retrieved %d chunks from collection '%s'.", len(chunks), collection)
    return chunks


def q_get_collection_name(repo_full_name: str, repo_id: str) -> str:
    """
    Create a Qdrant-safe collection name from repo_full_name and repo_id.
    Only allows alphanumeric, dash, and underscore.
    """
    safe_name = re.sub(r"[^a-zA-Z0-9_-]", "-", repo_full_name)
    return f"aibot-{safe_name}-{repo_id}"


def q_collection_exists(collection_name: str) -> bool:
    """
    Check if a collection exists in Qdrant.
    Returns True if the collection exists, False otherwise.
    """
    try:
        collections = q_client.get_collections()
        return any(c.name == collection_name for c in collections.collections)
    except Exception as e:
        logger.error("Failed to check collection existence for %s: %s", collection_name, str(e))
        return False


def q_process_remote_repo(
    repo_full_name: str,
    repo_id: str,
    gh_client: GitHubClient,
    target_branch: str = "main",
) -> str:
    repo_api_url = f"https://api.github.com/repos/{repo_full_name}"
    tree_url = f"{repo_api_url}/git/trees/{target_branch}?recursive=1"
    tree_data = gh_client.get(tree_url)
    tree_data = tree_data.json()
    logger.info("Fetching tree data for repo: %s (branch: %s)", repo_full_name, target_branch)
    logger.debug("Received tree data: %s", json.dumps(tree_data, indent=2))

    if not tree_data or "tree" not in tree_data:
        logger.error(
            "Malformed tree data for repo: %s. Ensure that the default branch is set to %s.",
            repo_full_name,
            target_branch,
        )
        raise ValueError(f"Invalid tree data received from GitHub API: {json.dumps(tree_data, indent=2)}")

    q_repo_name = sanitize_name(repo_full_name)

    qdrant_collection = q_get_collection_name(q_repo_name, repo_id)
    ensure_collection(qdrant_collection, QDRANT_VECTOR_SIZE)

    valid_items = filter_files_to_process(
        tree_data["tree"],
        path_key="path",
        size_key="size",
        type_key="type",
        skip_type_check=False,
        skip_size_check=False,
    )
    logger.info("Found %d valid files to process in repo: %s", len(valid_items), repo_full_name)

    for file_info in valid_items:
        logger.debug("Fetching content for file: %s (branch: %s)", file_info["path"], target_branch)

        try:
            content = gh_client.fetch_file_content(repo_full_name, file_info["path"], target_branch)
        except Exception as e:
            logger.warning(
                "Remote repo processing - failed to fetch raw content for %s: %s", file_info["path"], e, exc_info=True
            )
            continue

        if not content:
            logger.warning("Empty content for file: %s", file_info["path"])
            continue

        try:
            chunks: List[ChunkType] = chunk_file(content, file_info["path"])
            if not chunks:
                logger.warning("No chunks generated for file: %s", file_info["path"])
                continue

            chunks = postprocess_chunks(chunks)
        except Exception as e:
            logger.error("Error chunking file %s: %s", file_info["path"], e, exc_info=True)
            continue

        try:
            logger.info("Storing embeddings for file: %s", file_info["path"])
            generate_and_store_embeddings(chunks, qdrant_collection)
        except Exception as e:
            logger.error("Failed embeddings for file %s: %s", file_info["path"], e, exc_info=True)
            continue

    logger.info("Completed processing repo: %s -> Qdrant collection: %s", q_repo_name, qdrant_collection)
    return qdrant_collection


def q_process_repository(
    repo_obj: Dict[str, Any], installation: GithubAppInstallation, gh_client: GitHubClient
) -> Tuple[str | None, str | None]:
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
    except Exception:
        logger.error("Failed to process repo %s: failed to process repository", repo_obj.full_name, exc_info=True)
        repo_obj.state = RepoState.ERROR
        repo_obj.save()
        return None, repo_obj.full_name


def filter_files_to_process(
    file_items: Dict,
    path_key: str = "path",
    size_key: str = "size",
    type_key: str = "type",
    skip_type_check: bool = False,
    skip_size_check: bool = False,
) -> List[Dict]:
    valid_items = []
    for item in file_items:
        path = item.get(path_key, "")
        if not path:
            continue

        if should_skip_file(path):
            logger.debug("Skipping (from rules) %s", path)
            continue

        if not skip_type_check and item.get(type_key) != "blob":
            continue

        if not skip_size_check:
            size = item.get(size_key, 0)
            if size > MAX_FILE_SIZE:
                logger.debug("Skipping (too large %d): %s", size, path)
                continue

        valid_items.append(item)
    return valid_items


def generate_and_store_embeddings(chunks: List[ChunkType], qdrant_collection: str):
    """Generates embeddings and stores them in Qdrant."""
    for chunk in chunks:
        embedding = generate_embedding(chunk["content"], EmbeddingTaskType.RETRIEVAL_DOCUMENT)
        if embedding:
            logger.info("Upserting chunk from %s", chunk["file_path"])
            upsert_to_qdrant(qdrant_collection, chunk, embedding)


def q_rename_collection_alias(old_name: str, new_name: str, repo_id: str) -> None:
    """
    Rename a Qdrant collection alias safely.
    - Detects if `old_name` is an alias or a collection.
    - Handles renaming even if the new name matches an existing alias or collection.

    Args:
        old_name: The old full repo name (alias or collection name).
        new_name: The new full repo name (alias).
        repo_id: The repository ID used to build collection name.

    Raises:
        ValueError: If neither a collection nor alias for `old_name` exists.
    """
    old_q_name = q_get_collection_name(old_name, repo_id)
    new_q_name = q_get_collection_name(new_name, repo_id)

    logger.debug("RENAMING %s to %s", old_q_name, new_q_name)

    collections = {c.name for c in q_client.get_collections().collections}
    aliases_info = q_client.get_aliases().aliases
    aliases = {alias.alias_name: alias.collection_name for alias in aliases_info}

    if old_q_name in collections:
        collection_name = old_q_name
    elif old_q_name in aliases:
        collection_name = aliases[old_q_name]
    else:
        raise ValueError(f"No collection or alias named '{old_q_name}' exists in Qdrant.")

    ops = []

    if new_q_name in aliases:
        ops.append(models.DeleteAliasOperation(delete_alias=models.DeleteAlias(alias_name=new_q_name)))

    if new_q_name == collection_name:
        logger.info("New alias name '%s' is same as the collection; skipping alias creation.", new_q_name)
        return

    if old_q_name in aliases:
        ops.append(models.DeleteAliasOperation(delete_alias=models.DeleteAlias(alias_name=old_q_name)))

    ops.append(
        models.CreateAliasOperation(
            create_alias=models.CreateAlias(collection_name=collection_name, alias_name=new_q_name)
        )
    )

    try:
        q_client.update_collection_aliases(change_aliases_operations=ops)
        logger.info("Renamed alias from '%s' to '%s' (collection: %s).", old_q_name, new_q_name, collection_name)
    except Exception as e:
        logger.error("Failed to rename Qdrant alias from '%s' to '%s': %s", old_q_name, new_q_name, e)
        raise


def q_process_changed_files(
    changed_files: List[Dict], repo_full_name: str, repo_id: str, gh_client: GitHubClient
) -> None:
    collection_name = q_get_collection_name(repo_full_name, repo_id)
    ensure_collection(collection_name, QDRANT_VECTOR_SIZE)

    relevant_files = [f for f in changed_files if f["status"] in ("added", "modified", "renamed")]

    filtered_files = filter_files_to_process(
        relevant_files,
        path_key="path",
        skip_type_check=True,
        skip_size_check=True,
    )
    filtered_paths = {f["path"] for f in filtered_files}

    for file in changed_files:
        fpath = file["path"]
        status = file["status"]

        def delete_by_path(delete_path: str, reason: str):
            try:
                q_client.delete(
                    collection_name=collection_name,
                    points_selector=Filter(must=[FieldCondition(key="file_path", match=MatchValue(value=delete_path))]),
                )
                logger.info("Deleted embeddings for %s file: %s", reason, delete_path)
            except Exception as e:
                logger.error("Failed to delete %s file %s: %s", reason, delete_path, str(e))

        if status == "removed":
            delete_by_path(fpath, "removed")
            continue

        if status == "renamed" and file.get("previous_path"):
            delete_by_path(file["previous_path"], "renamed (old path)")

        if fpath not in filtered_paths:
            logger.debug("Skipping unprocessed file (filtered out): %s", fpath)
            continue

        delete_by_path(fpath, "existing")

        content = gh_client.fetch_file_content(repo_full_name, fpath, "main")
        logger.debug("Fetched content for %s (%d chars)", fpath, len(content))
        if not content:
            logger.warning("Could not fetch content for file: %s", fpath)
            continue

        try:
            chunks: ChunkType = chunk_file(content, fpath)
            if not chunks:
                logger.warning("No chunks for file: %s", fpath)
                continue
            chunks = postprocess_chunks(chunks)
            generate_and_store_embeddings(chunks, collection_name)
        except Exception as e:
            logger.error("Failed processing file %s: %s", fpath, e, exc_info=True)
