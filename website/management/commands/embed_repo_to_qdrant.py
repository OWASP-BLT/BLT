"""
Django management command for generating and storing code embeddings for repository files.

This module walks through the repository, processes Python files, splits them into logical code
chunks, generates embeddings using Google's Generative AI, and stores them in a Qdrant vector
database. It includes logic for chunking both general Python files and Django settings files,
and ensures the Qdrant collection exists before storing embeddings.
"""

import ast
import hashlib
import logging
import os
import time
from typing import Dict, List, Optional, Set, Tuple, Union
from uuid import UUID

import google.generativeai as genai
from django.conf import settings
from django.core.management.base import BaseCommand
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

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
        """Walks through the repository and processes each file."""
        for root, dirs, files in os.walk(self.repo_path):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for file in files:
                if self._should_skip_file(file):
                    continue
                self.process_file(os.path.join(root, file))

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


def extract_functions_and_classes(tree: ast.AST, lines: List[str], file_path: str) -> Tuple[List[ChunkType], Set[int]]:
    """
    Extract function and class definitions including decorators.
    """
    chunks = []
    covered_lines = set()

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start_line = node.lineno - 1
            if hasattr(node, "decorator_list") and node.decorator_list:
                decorator_lines = [d.lineno for d in node.decorator_list]
                start_line = min(min(decorator_lines) - 1, start_line)

            end_line = node.end_lineno
            code_chunk = "\n".join(lines[start_line:end_line])
            covered_lines.update(range(start_line, end_line))

            chunks.append(
                {
                    "type": "class" if isinstance(node, ast.ClassDef) else "function",
                    "name": getattr(node, "name", None),
                    "chunk": code_chunk,
                    "file": file_path,
                    "start_line": start_line + 1,
                    "end_line": end_line,
                }
            )

    return chunks, covered_lines


def extract_imports(tree: ast.AST, lines: List[str], file_path: str) -> Tuple[List[ChunkType], Set[int]]:
    """
    Extract all import statements as a single grouped chunk.
    """
    import_lines = []
    covered_lines = set()
    start_line = None
    end_line = None

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            node_start = node.lineno - 1
            node_end = getattr(node, "end_lineno", node.lineno)
            if start_line is None:
                start_line = node_start
            end_line = node_end
            import_lines.extend(lines[node_start:node_end])
            covered_lines.update(range(node_start, node_end))

    if not import_lines:
        return [], set()

    code_chunk = "\n".join(import_lines)
    chunk = {
        "type": "import_block",
        "name": "import statements",
        "chunk": code_chunk,
        "file": file_path,
        "start_line": start_line + 1,
        "end_line": end_line,
    }

    return [chunk], covered_lines


def extract_module_level_code(lines: List[str], covered_lines: Set[int], file_path: str) -> List[ChunkType]:
    """
    Extract remaining top-level code that wasn't captured.
    """
    chunks = []
    current_block = []

    for i, line in enumerate(lines):
        if i in covered_lines:
            if current_block:
                chunks.append(
                    {
                        "type": "module",
                        "name": None,
                        "chunk": "\n".join(current_block),
                        "file": file_path,
                        "start_line": i - len(current_block) + 1,
                        "end_line": i,
                    }
                )
                current_block = []
            continue

        if line.strip() == "":
            if current_block:
                chunks.append(
                    {
                        "type": "module",
                        "name": None,
                        "chunk": "\n".join(current_block),
                        "file": file_path,
                        "start_line": i - len(current_block) + 1,
                        "end_line": i,
                    }
                )
                current_block = []
        else:
            current_block.append(line)

    if current_block:
        chunks.append(
            {
                "type": "module",
                "name": None,
                "chunk": "\n".join(current_block),
                "file": file_path,
                "start_line": len(lines) - len(current_block) + 1,
                "end_line": len(lines),
            }
        )

    return chunks


def chunk_python_file(content: str, file_path: str) -> List[Dict[str, Union[str, int, None]]]:
    """
    Parse and split a Python file into meaningful logical chunks.

    This function uses AST parsing to extract classes, functions, and imports,
    then collects remaining top-level module-level code as a final chunk.

    Args:
        content (str): Full source code of the Python file.
        file_path (str): Path to the file for reference in metadata.

    Returns:
        List[Dict]: A list of dictionaries representing each chunk with keys like:
            - 'type': One of 'function', 'class', 'import', or 'module'
            - 'name': Optional name of the function/class/import
            - 'chunk': The actual code content of the chunk
            - 'file': File path (same for all chunks)
            - 'start_line': Start line number in the original file
            - 'end_line': End line number in the original file
    """
    logger.debug("Chunking file: %s", file_path)
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        logger.warning("Syntax error in %s: %s", file_path, e)
        return []

    lines = content.splitlines()

    func_chunks, func_lines = extract_functions_and_classes(tree, lines, file_path)
    import_chunks, import_lines = extract_imports(tree, lines, file_path)

    covered_lines = func_lines.union(import_lines)

    module_chunks = extract_module_level_code(lines, covered_lines, file_path)

    return func_chunks + import_chunks + module_chunks


def extract_if_blocks(tree: ast.AST, lines: List[str], file_path: str) -> List[ChunkType]:
    """
    Extract top-level if-blocks and return as chunks.
    """
    if_blocks = []
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.If):
            start_line = node.lineno - 1
            end_line = node.end_lineno
            code = "\n".join(lines[start_line:end_line])
            if_blocks.append(
                {
                    "type": "module",
                    "name": "if_block",
                    "chunk": code,
                    "file": file_path,
                    "start_line": start_line + 1,
                    "end_line": end_line,
                }
            )
    return if_blocks


def chunk_settings_files(content: str, file_path: str) -> List[Dict[str, Union[str, int, None]]]:
    """
    Parse and split a Django settings.py file into meaningful logical chunks.

    This function uses AST parsing to extract import statements and top-level if-blocks,
    then groups the remaining lines into blocks separated by empty lines or other
    structured content.

    Args:
        content (str): The full content of the settings.py file as a string.
        file_path (str): Path to the settings file for reference in metadata.

    Returns:
        List[Dict]: A list of dictionaries representing each chunk with keys like:
            - 'type': 'import' or 'module'
            - 'name': Optional title of the chunk
            - 'chunk': The actual code content of the chunk
            - 'file': File path (same for all chunks)
            - 'start_line': Start line number in the original file
            - 'end_line': End line number in the original file
    """
    logger.debug("Chunking settings file: %s", file_path)
    try:
        tree = ast.parse(content)
    except SyntaxError as e:
        logger.warning("Syntax error in %s: %s", file_path, e)
        return []
    lines = content.splitlines()

    imports, covered_lines = extract_imports(tree, lines, file_path)

    if_blocks = extract_if_blocks(tree, lines, file_path)

    misc_blocks = extract_module_level_code(lines, covered_lines, file_path)

    chunks = []
    if imports:
        chunks.extend(imports)
    chunks.extend(if_blocks)
    chunks.extend(misc_blocks)

    return chunks


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
            "Failed to create Qdrant collection. The collection could not be created. "
            "Please check your Qdrant server and configuration. Error: %s", str(e)
        )


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
