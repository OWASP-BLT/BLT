import logging
import os
from typing import Dict, List

from django.conf import settings
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from unidiff import PatchSet

from website.aibot.chunk_utils import chunk_file, postprocess_chunks
from website.aibot.clients import q_client
from website.aibot.models import PullRequest
from website.aibot.network import fetch_raw_content, generate_embedding, github_api_get
from website.aibot.types import ChunkType
from website.aibot.utils import generate_uuid, sanitize_name

logger = logging.getLogger(__name__)

EXTENSIONS_TO_PROCESS = {
    ".py",
    ".html",
    ".yml",
    ".yaml",
    ".json",
    ".md",
    ".txt",
}

SKIP_DIRS = {"migrations", "__pycache__", "static", "staticfiles", "media"}


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


def upsert_to_qdrant(q_client: QdrantClient, qdrant_collection: str, chunk: Dict, embedding: List[float]) -> None:
    """Upsert the embedding in specified Qdrant collection."""
    point = PointStruct(
        id=generate_uuid(chunk["file"], chunk["start_line"], chunk["end_line"]),
        vector=embedding,
        payload={
            "file_path": chunk["file"],
            "file_name": os.path.basename(chunk["file"]),
            "chunk": chunk["chunk"],
            "start_line": chunk["start_line"],
            "end_line": chunk["end_line"],
        },
    )
    q_client.upsert(
        collection_name=qdrant_collection,
        points=[point],
    )


def create_temp_pr_collection(pr_instance: PullRequest, patch: PatchSet) -> None:
    source_collection = "repo_embeddings"
    sanitized_head_ref = sanitize_backslash(pr_instance.head_branch)
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


def process_remote_repo(api_url: str, raw_content_url: str, repo_full_name: str, repo_id: str, branch="main"):
    tree_url = f"{api_url}/git/trees/{branch}?recursive=1"
    tree_data = github_api_get(tree_url)
    r_name = sanitize_name(repo_full_name)
    qdrant_collection = f"aibot-{r_name}-{repo_id}"

    valid_items = []

    def should_process_item(item: dict) -> bool:
        """
        Return True if the item is a file blob, not in a skipped directory,
        and has an allowed extension.
        """
        if item.get("type") != "blob":
            return False
        path = item.get("path", "")
        if not path:
            return False
        if any(path.startswith(skip_dir + "/") for skip_dir in SKIP_DIRS):
            return False
        _, ext = os.path.splitext(path)
        return ext in EXTENSIONS_TO_PROCESS

    for item in tree_data["tree"]:
        if not should_process_item(item):
            continue

        valid_items.append(item)

    for file_info in valid_items:
        raw_url = f"{raw_content_url}/{branch}/{file_info['path']}"

        content = fetch_raw_content(raw_url)

        if not content:
            continue

        chunks = chunk_file(content, file_info["path"])
        if not chunks:
            continue

        chunks = postprocess_chunks(chunks)
        generate_and_store_embeddings(chunks, qdrant_collection)


def generate_and_store_embeddings(chunks: List[ChunkType], qdrant_collection: str):
    """Generates embeddings and stores them in Qdrant."""
    for chunk in chunks:
        embedding = generate_embedding(chunk["content"], chunk["chunk_type"])
        if embedding:
            upsert_to_qdrant(q_client, qdrant_collection, chunk, embedding)
