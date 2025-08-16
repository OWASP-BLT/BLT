import json
import logging
import os
from typing import Dict, List

from django.conf import settings
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from unidiff import PatchSet

from website.aibot.chunk_utils import chunk_file, postprocess_chunks
from website.aibot.models import PullRequest
from website.aibot.network import fetch_raw_content, generate_embedding, github_api_get
from website.aibot.types import ChunkType
from website.aibot.utils import generate_uuid, sanitize_name

logger = logging.getLogger(__name__)

EXTENSIONS_TO_PROCESS = {
    # Code files
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".c",
    ".cpp",
    ".h",
    ".cs",
    ".swift",
    ".php",
    ".rb",
    ".sh",
    # Web files
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".less",
    # Config & data files
    ".yml",
    ".yaml",
    ".json",
    ".toml",
    ".ini",
    ".env",
    ".csv",
    ".xml",
    # Documentation
    ".md",
    ".txt",
    # Build/config (small, text-based)
    "Dockerfile",
    ".dockerfile",
    ".gitignore",
    ".gitattributes",
}

SKIP_DIRS = {
    # Dependency & runtime dirs (large, useless for RAG)
    "__pycache__",
    "node_modules",
    "venv",
    ".venv",
    "env",
    "vendor",
    "dist",
    "build",
    "target",
    # Cache & generated files
    ".cache",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "coverage",
    # Static assets (non-text)
    "static",
    "staticfiles",
    "media",
    "assets",
    "images",
    "fonts",
    # Version control & IDE
    ".git",
    ".idea",
    ".vscode",
    ".vs",
    # OS metadata
    ".DS_Store",
    "Thumbs.db",
}

MAX_FILE_SIZE = 1 * 1024 * 1024  # 1 MB


def ensure_collection(q_client: QdrantClient, qdrant_collection: str, qdrant_vector_size: int) -> None:
    """
    Ensure the Qdrant collection exists.

    Checks if the specified Qdrant collection exists, and creates it with the given vector size
    and cosine distance if it does not exist.
    """
    collections = [c.name for c in q_client.get_collections().collections]
    if qdrant_collection in collections:
        logger.debug("Qdrant collection '%s' already exists.", qdrant_collection)
        return
    try:
        q_client.create_collection(
            collection_name=qdrant_collection,
            vectors_config={"size": int(qdrant_vector_size), "distance": "Cosine"},
        )
        logger.debug("Created Qdrant collection '%s'", qdrant_collection)
    except Exception as e:
        logger.error(
            "Failed to create Qdrant collection. The collection could not be created."
            "Please check your Qdrant server and configuration. Error: %s",
            str(e),
        )
        raise


def upsert_to_qdrant(q_client: QdrantClient, qdrant_collection: str, chunk: ChunkType, embedding: List[float]) -> None:
    """Upsert the embedding in specified Qdrant collection."""
    point = PointStruct(
        id=generate_uuid(chunk["file_path"], chunk["start_line"], chunk["end_line"]),
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
    q_client.upsert(
        collection_name=qdrant_collection,
        points=[point],
    )


def create_temp_pr_collection(q_client: QdrantClient, pr_instance: PullRequest, patch: PatchSet) -> None:
    source_collection = "repo_embeddings"
    sanitized_head_ref = sanitize_name(pr_instance.head_branch)
    temp_collection = f"temp_{sanitized_head_ref}_{pr_instance.number}"
    ensure_collection(q_client, source_collection, settings.QDRANT_VECTOR_SIZE)
    ensure_collection(q_client, temp_collection, settings.QDRANT_VECTOR_SIZE)

    for file in patch:
        if file.is_modified_file:
            fpath = file.source_file
            if file.is_rename:
                fpath = file.target_file
            fpath = fpath[2:]
            f_raw_url = pr_instance.raw_url_map.get(fpath, None)
            if f_raw_url:
                content = fetch_raw_content(f_raw_url)
            else:
                logger.warning("Could not find raw url mapping for patch file: %s", fpath)
            if not content:
                continue
            chunks = chunk_file(content, fpath)

            for chunk in chunks:
                embedding = generate_embedding(chunk["chunk"], chunk.get("name"))
                if embedding:
                    upsert_to_qdrant(q_client, temp_collection, chunk, embedding)

    return source_collection, temp_collection


def get_similar_merged_chunks(
    q_client: QdrantClient,
    source_collection: str,
    temp_collection: str,
    query: str,
    k: int,
    rename_mappings: Dict[str, str],
) -> List[ChunkType]:
    main_points = q_client.query_points(collection_name=source_collection, query=query, limit=k)
    temp_points = q_client.query_points(collection_name=temp_collection, query=query, limit=k)

    relevant_chunks: Dict[str, ChunkType] = {}
    overwrite_log = []

    for point in main_points.points:
        chunk_data = point.payload
        key = chunk_data.get("file") or chunk_data.get("file_path")
        relevant_chunks[key] = chunk_data

    for point in temp_points.points:
        chunk_data = point.payload
        key = chunk_data.get("file") or chunk_data.get("file_path")
        if key in relevant_chunks:
            log_entry = {
                "original_key": key,
                "action": "overwritten",
                "new_key": rename_mappings.get(key, key),
                "old_chunk_preview": relevant_chunks[key],
            }
            overwrite_log.append(log_entry)
            logger.info("Found existing key: %s. Overwriting", key)
            del relevant_chunks[key]
            key = rename_mappings.get(key, key)
        relevant_chunks[key] = chunk_data

    return list(relevant_chunks.values())


def q_get_collection_name(repo_full_name: str, repo_id: str) -> str:
    return f"aibot-{repo_full_name}-{repo_id}"


def q_collection_exists(q_client: QdrantClient, collection_name: str) -> bool:
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


def q_process_remote_repote_repo(
    q_client: QdrantClient, repo_full_name: str, repo_id: str, target_branch="main"
) -> str:
    repo_api_url = f"https://api.github.com/repos/{repo_full_name}"
    raw_content_url = f"https://raw.githubusercontent.com/{repo_full_name}/{target_branch}"
    tree_url = f"{repo_api_url}/git/trees/{target_branch}?recursive=1"
    tree_data = github_api_get(tree_url)

    logger.info("Fetching tree data for repo: %s (branch: %s)", repo_full_name, target_branch)

    if not tree_data or "tree" not in tree_data:
        logger.error("Malformed tree data for repo: %s", repo_full_name)
        raise ValueError("Invalid tree data received from GitHub API")

    tree_data = json.loads(tree_data)
    repo_full_name = sanitize_name(repo_full_name)

    qdrant_collection = q_get_collection_name(repo_full_name, repo_id)

    logger.info("Ensuring Qdrant collection: %s", qdrant_collection)
    ensure_collection(q_client, qdrant_collection, settings.QDRANT_VECTOR_SIZE)

    valid_items = []
    for item in tree_data["tree"]:
        if item.get("type") != "blob":
            continue

        path = item.get("path", "")
        if not path:
            continue

        if any(path.startswith(skip_dir + "/") or f"/{skip_dir}/" in path for skip_dir in SKIP_DIRS):
            logger.debug("Skipping file due to directory exclusion: %s", path)
            continue

        _, ext = os.path.splitext(path)
        if ext.lower() not in EXTENSIONS_TO_PROCESS:
            logger.debug("Skipping unsupported extension: %s", path)
            continue

        if item.get("size", 0) > MAX_FILE_SIZE:
            logger.debug("Skipping file due to size limit: %s (%d bytes)", path, item.get("size", 0))
            continue

        valid_items.append(item)

    logger.info("Found %d valid files to process in repo: %s", len(valid_items), repo_full_name)

    for file_info in valid_items:
        raw_url = f"{raw_content_url}/{file_info['path']}"
        logger.debug("Fetching raw content from: %s", raw_url)

        try:
            content = fetch_raw_content(raw_url)
        except Exception as e:
            logger.warning("Failed to fetch raw content for %s: %s", file_info["path"], e, exc_info=True)
            continue

        if not content:
            logger.warning("Empty content for file: %s", file_info["path"])
            continue

        try:
            chunks = chunk_file(content, file_info["path"])
            if not chunks:
                logger.warning("No chunks generated for file: %s", file_info["path"])
                continue

            chunks = postprocess_chunks(chunks)
        except Exception as e:
            logger.error("Error chunking file %s: %s", file_info["path"], e, exc_info=True)
            continue

        try:
            logger.info("Storing embeddings for file: %s", file_info["path"])
            generate_and_store_embeddings(q_client, chunks, qdrant_collection)
        except Exception as e:
            logger.error("Failed embeddings for file %s: %s", file_info["path"], e, exc_info=True)
            continue

    logger.info("Completed processing repo: %s → Qdrant collection: %s", repo_full_name, qdrant_collection)
    return qdrant_collection


def generate_and_store_embeddings(q_client: QdrantClient, chunks: List[ChunkType], qdrant_collection: str):
    """Generates embeddings and stores them in Qdrant."""
    for chunk in chunks:
        embedding = generate_embedding(chunk["content"], chunk["chunk_type"])
        if embedding:
            upsert_to_qdrant(q_client, qdrant_collection, chunk, embedding)


def rename_qdrant_collection_with_alias(q_client: QdrantClient, old_name: str, new_name: str) -> None:
    """
    Rename a Qdrant collection by creating an alias for the new name.

    Args:
        q_client (QdrantClient): The Qdrant client instance.
        old_name (str): The current name of the collection.
        new_name (str): The new name for the collection.

    Raises:
        ValueError: If the old collection does not exist.
    """
    collections = [c.name for c in q_client.get_collections().collections]

    if old_name not in collections:
        raise ValueError(f"Collection '{old_name}' does not exist in Qdrant.")

    q_client.create_alias(alias_name=new_name, collection_name=old_name)
    logger.info("Created alias '%s' for collection '%s'.", new_name, old_name)

    q_client.delete_alias(alias_name=old_name)
    logger.info("Removed alias '%s'.", old_name)


def q_process_changed_files(
    q_client: QdrantClient, changed_files: List[Dict], repo_full_name: str, repo_id: str
) -> None:
    collection_name = q_get_collection_name(repo_full_name, repo_id)
    ensure_collection(q_client, collection_name, settings.QDRANT_VECTOR_SIZE)

    for file in changed_files:
        path = file["path"]
        status = file["status"]

        if status == "removed":
            try:
                q_client.delete(
                    collection_name=collection_name,
                    points_selector={"filter": {"must": [{"key": "file_path", "match": {"value": path}}]}},
                )
                logger.info("Deleted embeddings for removed file: %s", path)
            except Exception as e:
                logger.error("Failed to delete removed file %s from Qdrant: %s", path, str(e))
            continue

        if status == "renamed" and file.get("previous_path"):
            old_path = file["previous_path"]
            try:
                q_client.delete(
                    collection_name=collection_name,
                    points_selector={"filter": {"must": [{"key": "file_path", "match": {"value": old_path}}]}},
                )
                logger.info("Deleted embeddings for renamed file (old path): %s", old_path)
            except Exception as e:
                logger.error("Failed to delete old path %s in Qdrant: %s", old_path, str(e))

        try:
            q_client.delete(
                collection_name=collection_name,
                points_selector={"filter": {"must": [{"key": "file_path", "match": {"value": path}}]}},
            )
            logger.info("Deleted old embeddings for file: %s", path)
        except Exception as e:
            logger.error("Failed to delete embeddings for %s: %s", path, str(e))

        raw_url = f"https://raw.githubusercontent.com/{repo_full_name}/main/{path}"
        content = fetch_raw_content(raw_url)
        if not content:
            logger.warning("Could not fetch raw content for file: %s", path)
            continue

        chunks = chunk_file(content, path)
        for chunk in chunks:
            embedding = generate_embedding(chunk["chunk"], chunk.get("name"))
            if embedding:
                upsert_to_qdrant(q_client, collection_name, chunk, embedding)

    return
