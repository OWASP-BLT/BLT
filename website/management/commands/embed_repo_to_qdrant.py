"""
Django management command for generating and storing code embeddings for repository files.

This module walks through the repository, processes Python files, splits them into logical code
chunks, generates embeddings using Google's Generative AI, and stores them in a Qdrant vector
database. It includes logic for chunking both general Python files and Django settings files,
and ensures the Qdrant collection exists before storing embeddings.
"""

import hashlib
import logging
import os
import time
from typing import Dict, List, Optional, Union
from uuid import UUID

import google.generativeai as genai
from django.conf import settings
from django.core.management.base import BaseCommand
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from parse_utils import chunk_python_file, chunk_settings_files

logger = logging.getLogger(__name__)

ChunkType = Dict[str, Union[str, int, None]]

EXTENSIONS = {
    ".py",
}

SKIP_DIRS = {"migrations", "__pycache__"}


def initialize_settings():
    """Check and load all required settings, fail fast if missing."""
    missing = []
    qdrant_collection = os.environ.get("QDRANT_COLLECTION")
    qdrant_host = os.environ.get("QDRANT_HOST")
    qdrant_http_port = os.environ.get("QDRANT_HTTP_PORT")
    qdrant_vector_size = os.environ.get("QDRANT_VECTOR_SIZE")
    gemini_api_key = os.environ.get("GEMINI_API_KEY")
    repo_path = getattr(settings, "BASE_DIR", None)

    if not qdrant_collection:
        missing.append("QDRANT_COLLECTION")
    if not qdrant_host:
        missing.append("QDRANT_HOST")
    if not qdrant_http_port:
        missing.append("QDRANT_HTTP_PORT")
    if not qdrant_vector_size:
        missing.append("QDRANT_VECTOR_SIZE")
    if not gemini_api_key:
        missing.append("GEMINI_API_KEY")
    if not repo_path:
        missing.append("BASE_DIR (from Django settings)")

    if missing:
        raise RuntimeError(
            f"The following required settings are missing: {', '.join(missing)}. "
            "Please set them in your environment or Django settings before running this command."
        )

    try:
        qdrant_vector_size = int(qdrant_vector_size)
        qdrant_http_port = int(qdrant_http_port)
    except ValueError as e:
        raise RuntimeError(f"Invalid numeric value for QDRANT_VECTOR_SIZE or QDRANT_HTTP_PORT: {e}") from e

    return {
        "QDRANT_COLLECTION": qdrant_collection,
        "QDRANT_HOST": qdrant_host,
        "QDRANT_HTTP_PORT": qdrant_http_port,
        "QDRANT_VECTOR_SIZE": qdrant_vector_size,
        "GEMINI_API_KEY": gemini_api_key,
        "REPO_PATH": repo_path,
    }


def configure_genai(api_key: str):
    """Configure the Google Generative AI client."""
    genai.configure(api_key=api_key)


class Command(BaseCommand):
    """
    Django management command for generating and storing text embeddings from repository files.
    This command walks through a specified repository, processes each file
    (with support for chunking and skipping non-relevant files), generates embeddings using
    the Gemini API, and stores the resulting vectors in a Qdrant vector database.
    It delegates chunking logic based on file type.

    Attributes:
        qdrant_client (QdrantClient): Client for interacting with the Qdrant vector database.
        embedding_model (str): The embedding model used for generating text embeddings.

    Methods:
        handle(*args, **options): Initiates the embedding generation process.
        process_repository_files(): Walks through the repository and processes each file.
        process_file(file_path): Processes a single file by reading, chunking, and
        storing embeddings.
        _should_skip_file(file): Determines if a file should be skipped based on its extension.
        _read_file(file_path): Reads the content of a file with error handling.
        _chunk_file(content, file_path): Delegates chunking to the appropriate function
        based on file type.
        _store_embeddings(chunks): Generates embeddings for file chunks and stores them in Qdrant.
        _generate_embedding(text, title): Calls the Gemini API to generate an embedding for
        a text chunk.
        _upsert_to_qdrant(chunk, embedding): Stores the embedding and associated metadata in Qdrant.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        config = initialize_settings()
        self.qdrant_collection = config["QDRANT_COLLECTION"]
        self.qdrant_vector_size = config["QDRANT_VECTOR_SIZE"]
        self.gemini_api_key = config["GEMINI_API_KEY"]
        self.repo_path = config["REPO_PATH"]

        self.qdrant_client = QdrantClient(host=config["QDRANT_HOST"], port=config["QDRANT_HTTP_PORT"])
        self.embedding_model = "models/text-embedding-004"
        configure_genai(self.gemini_api_key)

    def handle(self, *args, **options):
        """Calls the embedding generation process."""
        ensure_collection(self.qdrant_client, self.qdrant_collection, self.qdrant_vector_size)
        self.process_repository_files()

    def process_repository_files(self):
        """Walks through the repository, collects valid files, and processes them."""
        file_paths = []
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for file in files:
                if self._should_skip_file(file):
                    continue
                file_path = os.path.join(root, file)
                file_paths.append(file_path)

        total_files = len(file_paths)
        logger.info("Found %d files to process.", total_files)

        for i, file_path in enumerate(file_paths, 1):
            self.process_file(file_path)
            if i % 10 == 0 or i == total_files:
                logger.info("Processed %d/%d files.", i, total_files)

    def process_file(self, file_path: str):
        """Processes a single file: reads, chunks, and stores embeddings."""
        content = self._read_file(file_path)
        if not content:
            return

        chunks = self._chunk_file(content, file_path)
        if not chunks:
            return

        self._store_embeddings(chunks)

    def _should_skip_file(self, file: str) -> bool:
        """Determines if a file should be skipped (e.g., non-Python files)."""
        _, ext = os.path.splitext(file)
        return ext not in EXTENSIONS

    def _read_file(self, file_path: str) -> str:
        """Reads file content with error handling."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except (IOError, UnicodeDecodeError) as e:
            logger.error("Error reading %s: %s", file_path, e)
            return ""

    def _chunk_file(self, content: str, file_path: str) -> List[Dict]:
        """Delegates to appropriate chunker based on file type."""
        if os.path.basename(file_path) == "settings.py":
            return chunk_settings_files(content, file_path)
        return chunk_python_file(content, file_path)

    def _store_embeddings(self, chunks: List[Dict]):
        """Generates embeddings and stores them in Qdrant."""
        for chunk in chunks:
            embedding = self._generate_embedding(chunk["chunk"], chunk.get("name"))
            if embedding:
                self._upsert_to_qdrant(chunk, embedding)

    def _generate_embedding(self, text: str, title: str = None) -> Optional[List[float]]:
        max_retries = 3
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                response = genai.embed_content(
                    model=self.embedding_model,
                    content=text,
                    task_type="retrieval_document",
                    title=title or "Untitled",
                )
                return response.get("embedding")
            except Exception as e:
                last_error = str(e)
                error_message = last_error.lower()
                if "rate limit" in error_message or "quota" in error_message or "timeout" in error_message:
                    logger.warning(
                        "Embedding generation attempt %d/%d failed due to a temporary error. Retrying...",
                        attempt,
                        max_retries,
                    )
                    time.sleep(2**attempt)
                else:
                    logger.error(
                        "Embedding generation failed due to a non-retryable error. The error was: %s", last_error
                    )
                    break
        logger.error(
            "Embedding generation failed after %d attempts. The error was: %s",
            max_retries,
            last_error or "Unknown error",
        )
        return None

    def _upsert_to_qdrant(self, chunk: Dict, embedding: List[float]):
        """Stores the embedding in Qdrant."""
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
        self.qdrant_client.upsert(
            collection_name=self.qdrant_collection,
            points=[point],
        )


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


def generate_uuid(file: str, start: int, end: int) -> str:
    """
    Generate a deterministic UUID from file path and line numbers.

    Args:
        file (str): File path or name.
        start (int): Start line number.
        end (int): End line number.

    Returns:
        str: A UUID string generated from the input values.
    """
    raw = f"{file}:{start}:{end}"
    hash_str = hashlib.sha256(raw.encode()).hexdigest()[:32]
    return str(UUID(hex=hash_str))
