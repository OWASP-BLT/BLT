import logging

from django.conf import settings
from qdrant_client import QdrantClient
from unidiff import PatchSet

from website.aibot.clients import q_client
from website.aibot.utils import sanitize_backslash

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


def create_temp_pr_collection(head_ref: str, pr_number: int, patch: PatchSet) -> None:
    source_collection = "repo_embeddings"
    sanitized_head_ref = sanitize_backslash(head_ref)
    target_collection = f"temp_{sanitized_head_ref}_{pr_number}"
    ensure_collection(q_client, source_collection, settings.QDRANT_VECTOR_SIZE)
    ensure_collection(q_client, target_collection, settings.QDRANT_VECTOR_SIZE)

    for file in patch:
        if file.is_modified_file:
            fpath = file.source_file
            if file.is_rename:
                fpath = file.target_file
            fpath = fpath[2:]
            content = _fetch_file_content("https://raw.githubusercontent.com/OWASP-BLT/BLT", head_ref, fpath)
            if not content:
                continue
            chunks = chunk_file(content, fpath)

            for chunk in chunks:
                embedding = generate_embedding(chunk["chunk"], chunk.get("name"))
                if embedding:
                    upsert_to_qdrant(qdrant_client, target_collection, chunk, embedding)

    return target_collection
