"""
Django management command for generating and storing code embeddings for repository files.

This module walks through the repository, processes Python files, splits them into logical code
chunks, generates embeddings using Google's Generative AI, and stores them in a Qdrant vector
database. It includes logic for chunking both general Python files and Django settings files,
and ensures the Qdrant collection exists before storing embeddings.
"""

import logging
import os
from typing import Dict, List

import google.generativeai as genai
from django.conf import settings
from django.core.management.base import BaseCommand
from tqdm import tqdm

from clients import qdrant_client
from parse_utils import (
    chunk_file,
    ensure_collection,
    generate_embedding,
    get_git_root,
    postprocess_chunks,
    upsert_to_qdrant,
)

logger = logging.getLogger(__name__)

EXTENSIONS = {
    ".py",
    ".html",
    ".yml",
    ".yaml",
    ".json",
    ".md",
    ".txt",
}

SKIP_DIRS = {"migrations", "__pycache__", "static", "staticfiles", "media"}


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

        self.qdrant_client = qdrant_client
        self.embedding_model = "models/text-embedding-004"
        configure_genai(self.gemini_api_key)

    def handle(self, *args, **options):
        """Calls the embedding generation process."""
        ensure_collection(self.qdrant_client, self.qdrant_collection, self.qdrant_vector_size)
        qdrant_logger = logging.getLogger("qdrant_client")
        original_level = qdrant_logger.getEffectiveLevel()
        qdrant_logger.setLevel(logging.WARNING)
        try:
            with tqdm.external_write_mode():
                self.process_repository_files()
        finally:
            qdrant_logger.setLevel(original_level)

    def process_repository_files(self):
        """Walks through the repository, collects valid files, and processes them."""
        repo_root = get_git_root(self.repo_path)
        logger.info("Repository root: %s", repo_root)
        file_paths = []
        for root, dirs, files in tqdm(os.walk(repo_root), desc="Scanning repository"):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for file in files:
                if self._should_skip_file(file):
                    continue
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, repo_root)
                file_paths.append(rel_path)

        total_files = len(file_paths)
        logger.info("Found %d files to process.", total_files)

        for file_path in tqdm(file_paths, desc="Processing files", position=0, leave=True):
            self.process_file(file_path)

    def process_file(self, file_path: str):
        """Processes a single file: reads, chunks, and stores embeddings."""
        content = self._read_file(file_path)
        if not content:
            return

        chunks = chunk_file(content, file_path)
        if not chunks:
            return

        chunks = postprocess_chunks(chunks)

        self._generate_and_store_embeddings(chunks)

    def _should_skip_file(self, file: str) -> bool:
        """Determines if a file should be skipped"""
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

    def _generate_and_store_embeddings(self, chunks: List[Dict]):
        """Generates embeddings and stores them in Qdrant."""
        for chunk in chunks:
            embedding = generate_embedding(chunk["chunk"], chunk.get("name"))
            if embedding:
                upsert_to_qdrant(qdrant_client, self.qdrant_collection, chunk, embedding)
