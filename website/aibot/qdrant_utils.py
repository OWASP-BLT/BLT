import logging
import os
from typing import Dict, List

from django.conf import settings
from models import PullRequest
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from unidiff import PatchSet

from website.aibot.chunk_utils import chunk_file
from website.aibot.clients import q_client
from website.aibot.network import fetch_raw_content, generate_embedding
from website.aibot.utils import _generate_uuid, sanitize_backslash

logger = logging.getLogger(__name__)


def ensure_collection(qdrant_client: QdrantClient, qdrant_collection: str, qdrant_vector_size: int) -> None:
    """
    Ensure the Qdrant collection exists.

    Checks if the specified Qdrant collection exists, and creates it with the given vector size
    and cosine distance if it does not exist.
    """
    collections = [c.name for c in qdrant_client.get_collections().collections]
    if qdrant_collection in collections:
        logger.debug("Qdrant collection '%s' already exists.", qdrant_collection)
        return
    try:
        qdrant_client.create_collection(
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


def upsert_to_qdrant(qdrant_client: QdrantClient, qdrant_collection: str, chunk: Dict, embedding: List[float]) -> None:
    """Upsert the embedding in specified Qdrant collection."""
    point = PointStruct(
        id=_generate_uuid(chunk["file"], chunk["start_line"], chunk["end_line"]),
        vector=embedding,
        payload={
            "file_path": chunk["file"],
            "file_name": os.path.basename(chunk["file"]),
            "chunk": chunk["chunk"],
            "start_line": chunk["start_line"],
            "end_line": chunk["end_line"],
        },
    )
    qdrant_client.upsert(
        collection_name=qdrant_collection,
        points=[point],
    )


def create_temp_pr_collection(pr_instance: PullRequest, patch: PatchSet) -> None:
    source_collection = "repo_embeddings"
    sanitized_head_ref = sanitize_backslash(pr_instance.head_branch)
    target_collection = f"temp_{sanitized_head_ref}_{pr_instance.number}"
    ensure_collection(q_client, source_collection, settings.QDRANT_VECTOR_SIZE)
    ensure_collection(q_client, target_collection, settings.QDRANT_VECTOR_SIZE)

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
                    upsert_to_qdrant(q_client, target_collection, chunk, embedding)

    return target_collection
