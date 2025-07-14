import ast
import hashlib
import json
import logging
import math
import os
import re
import time
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple, TypedDict
from uuid import UUID

import yaml
from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

from clients import genai

MAX_TOKENS = 1500
OVERLAP_LINES = 7
CHUNK_OVERLAP = 200

logger = logging.getLogger(__name__)


class ChunkType(TypedDict, total=False):
    """Represents a chunk of code extracted from a Python file."""

    type: str
    name: str
    chunk: str
    file: str
    start_line: int
    end_line: int
    part_index: int
    part_total: int


def _split_chunk_lines(
    chunk: ChunkType, total_tokens: int, max_tokens: int = MAX_TOKENS, overlap: int = OVERLAP_LINES
) -> List[ChunkType]:
    """Returns a list of smaller, overlapping chunks."""
    code_lines = chunk["chunk"].splitlines(keepends=True)
    n_parts = math.ceil(total_tokens / max_tokens)
    total_code_lines = len(code_lines)
    lines_per_part = math.ceil(total_code_lines / n_parts)
    mini_chunks: List[ChunkType] = []

    for part_idx in range(n_parts):
        start_idx = part_idx * n_parts

        if part_idx != 0:
            start_idx -= overlap
        end_idx = min(start_idx + lines_per_part + overlap, total_code_lines)
        snippet = "".join(code_lines[start_idx:end_idx])

        if not snippet.strip():
            continue

        mini_chunks.append(
            ChunkType(
                type=chunk["type"],
                name=chunk["name"],
                chunk=snippet,
                file=chunk["file"],
                start_line=chunk["start_line"] + start_idx + 1,
                end_line=chunk["end_line"] + end_idx,
                part_index=part_idx,
                part_total=n_parts,
            )
        )
    return mini_chunks


def postprocess_chunks(chunks: List[ChunkType]) -> List[ChunkType]:
    """
    Ensure chunks are non empty, under MAX_TOKENS,
    and split oversized ones with OVERLAP_LINES line overlap.
    """
    processed_chunks: List[ChunkType] = []

    for chunk in chunks:
        if not chunk["chunk"].strip():
            continue

        token_count = approximate_token_count_char(chunk["chunk"])

        if token_count <= MAX_TOKENS:
            processed_chunks.append(chunk)
        else:
            processed_chunks.extend(_split_chunk_lines(chunk, token_count))

    return processed_chunks


def chunk_file(content: str, file_path: str) -> List[ChunkType]:
    """Delegates to appropriate chunker based on file type."""
    file_path_lower = file_path.lower()
    file_name = os.path.basename(file_path_lower)
    chunkers = {
        "settings.py": chunk_settings_files,
        ".py": chunk_python_file,
        ".html": chunk_html_file,
        ".htm": chunk_html_file,
        ".jinja": chunk_html_file,
        ".yaml": chunk_yaml_file,
        ".yml": chunk_yaml_file,
        ".json": chunk_json_file,
        ".md": chunk_md_file,
        ".txt": chunk_text_file,
    }
    for pattern, chunker in chunkers.items():
        if file_name == pattern or file_path_lower.endswith(pattern):
            return chunker(content, file_path)
    logger.warning(f"Unsupported file type: {file_path}")
    return []


def chunk_text_file(content: str, file_path: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> List[ChunkType]:
    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ". ", " "],
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )

    chunks = splitter.split_text(content)

    return [
        ChunkType(
            type="text_paragraph",
            name=f"Text Chunk {i+1}",
            chunk=chunk,
            file=file_path,
            start_line=-1,
            end_line=-1,
            part_index=0,
            part_total=1,
        )
        for i, chunk in enumerate(chunks)
    ]


def chunk_md_file(content: str, file_path: str) -> List[ChunkType]:
    """Split markdown content by headings and return structured chunks."""
    headers_to_split_on = [
        ("#", "Section"),
        ("##", "Subsection"),
    ]

    try:
        splitter = MarkdownHeaderTextSplitter(headers_to_split_on)
        document_chunks = splitter.split_text(content)
    except Exception as e:
        print(f"Error processing markdown in {file_path}: {e}")
        return []

    chunks: List[ChunkType] = []

    for doc in document_chunks:
        name = doc.metadata.get("Subsection") or doc.metadata.get("Section") or "Root Content"
        final_content = f"{name} \n {doc.page_content}"

        chunks.append(
            ChunkType(
                type="markdown_section",
                name=name,
                chunk=final_content,
                file=file_path,
                start_line=-1,
                end_line=-1,
                part_index=0,
                part_total=1,
            )
        )

    return chunks


def chunk_json_file(content: str, file_path: str) -> List[ChunkType]:
    try:
        json_content = json.loads(content)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {file_path}: {e}")
        return []

    chunks: List[ChunkType] = []

    if isinstance(json_content, list):
        # Case 1: It's an array of objects
        for idx, item in enumerate(json_content):
            if isinstance(item, dict):
                chunks.append(
                    {
                        "type": "json_array_item",
                        "name": f"Item {idx + 1}",
                        "chunk": json.dumps(item, indent=2),
                        "file": file_path,
                        "start_line": -1,
                        "end_line": -1,
                        "part_index": idx + 1,
                        "part_total": len(json_content),
                    }
                )
    elif isinstance(json_content, dict):
        items = list(json_content.items())
        values_are_objects = all(isinstance(v, dict) for v in json_content.values())

        if values_are_objects and len(json_content) > 0:
            # Case 2: Nested object like {"k1": {}, "k2": {}}
            for idx, (key, value) in enumerate(items):
                chunks.append(
                    {
                        "type": "json_nested_object",
                        "name": key,
                        "chunk": json.dumps(value, indent=2),
                        "file": file_path,
                        "start_line": -1,
                        "end_line": -1,
                        "part_index": idx + 1,
                        "part_total": len(items),
                    }
                )
        else:
            chunks.append(
                {
                    "type": "json_full_object",
                    "name": "Root Object",
                    "chunk": json.dumps(json_content, indent=2),
                    "file": file_path,
                    "start_line": -1,
                    "end_line": -1,
                    "part_index": 1,
                    "part_total": 1,
                }
            )
    else:
        pass

    return chunks


def chunk_yaml_file(content: str, file_path: str) -> List[ChunkType]:
    yml_json = cvt_yml_to_json(content, file_path)
    yml_string = generate_yml_string(yml_json, file_path)

    level_1_settings = []
    group_chunks = []
    groups = defaultdict(str)
    for line in yml_string:
        main_key, value = line.split(":")
        keys = main_key.split(".")
        level = len(keys)
        if level == 1:
            level_1_settings.append(line)
        elif level == 2:
            level_1_key = keys[0]
            groups[level_1_key] += keys[1] + ":" + value + "\n"
        else:
            level_2_key = keys[0] + "." + keys[1]
            remainder_keys = ".".join(keys[2:])
            groups[level_2_key] += remainder_keys + ":" + value + "\n"

    level_1_code = "\n".join(level_1_settings)
    level_1_chunk = ChunkType(
        type="yaml",
        name="level 1 settings",
        chunk=level_1_code,
        file=file_path,
        start_line=-1,
        end_line=-1,
        part_index=0,
        part_total=1,
    )
    group_chunks = []

    for group_name, group_content in groups.items():
        group_content = group_content.rstrip("\n")
        group_chunk = ChunkType(
            type="yaml",
            name=f"{group_name}",
            chunk=group_content,
            file=file_path,
            start_line=-1,
            end_line=-1,
            part_index=0,
            part_total=1,
        )
        group_chunks.append(group_chunk)

    return [level_1_chunk] + group_chunks


def chunk_html_file(content: str, file_path: str) -> List[ChunkType]:
    """As of now, there is no specific implementation for html files. It simply creates a chunk
    of the entire file and returns it, so that it is directly handled by the postprocessing of chunks.
    """
    logger.debug("Chunking file: %s", file_path)
    lines = content.splitlines()
    chunk = ChunkType(
        type="html",
        name="html",
        chunk=content,
        file=file_path,
        start_line=1,
        end_line=len(lines),
        part_index=0,
        part_total=1,
    )
    return [chunk]


def chunk_python_file(content: str, file_path: str) -> List[ChunkType]:
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
    chunks = []
    chunks.extend(func_chunks)
    chunks.extend(import_chunks)
    chunks.extend(module_chunks)

    chunks.sort(key=lambda x: x["start_line"])

    return chunks


def chunk_settings_files(content: str, file_path: str) -> List[ChunkType]:
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

    imports, import_lines = extract_imports(tree, lines, file_path)
    if_blocks, if_lines = extract_if_blocks(tree, lines, file_path)
    try_blocks, try_lines = extract_try_blocks(tree, lines, file_path)

    covered_lines = import_lines.union(if_lines, try_lines)

    module_chunks = extract_module_level_code(lines, covered_lines, file_path)

    chunks = []
    chunks.extend(imports)
    chunks.extend(if_blocks)
    chunks.extend(try_blocks)
    chunks.extend(module_chunks)

    chunks.sort(key=lambda x: x["start_line"])
    return chunks


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


def extract_if_blocks(tree: ast.AST, lines: List[str], file_path: str) -> Tuple[List[ChunkType], Set[int]]:
    """
    Extract top-level if-blocks and return as chunks along with covered line numbers.
    """
    if_blocks = []
    covered_lines = set()

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.If):
            start_line = node.lineno - 1
            end_line = node.end_lineno
            code = "\n".join(lines[start_line:end_line])
            covered_lines.update(range(start_line, end_line))

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

    return if_blocks, covered_lines


def extract_try_blocks(tree: ast.AST, lines: List[str], file_path: str) -> Tuple[List[ChunkType], Set[int]]:
    """
    Extract try-except blocks and return as chunks along with covered line numbers.
    """
    try_blocks = []
    covered_lines = set()

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Try):
            start_line = node.lineno - 1
            end_line = node.end_lineno
            code = "\n".join(lines[start_line:end_line])
            covered_lines.update(range(start_line, end_line))

            try_blocks.append(
                {
                    "type": "try_block",
                    "name": "try_except",
                    "chunk": code,
                    "file": file_path,
                    "start_line": start_line + 1,
                    "end_line": end_line,
                }
            )

    return try_blocks, covered_lines


def generate_embedding(
    text: str, title: str = None, embedding_model="models/text-embedding-004"
) -> Optional[List[float]]:
    max_retries = 3
    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            response = genai.embed_content(
                model=embedding_model,
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
                logger.error("Embedding generation failed due to a non-retryable error. The error was: %s", last_error)
                break
    logger.error(
        "Embedding generation failed after %d attempts. The error was: %s",
        max_retries,
        last_error or "Unknown error",
    )
    return None


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


def _generate_uuid(file: str, start: int, end: int) -> str:
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


def get_git_root(path: str) -> str:
    """Returns the Git root directory for the given path."""
    if os.path.isfile(path):
        path = os.path.dirname(path)

    prev = None
    while path != prev:
        git_dir = os.path.join(path, ".git")
        if os.path.isdir(git_dir):
            return path
        prev = path
        path = os.path.dirname(path)

    # Final check at root level (e.g., '/' or 'C:\\')
    if os.path.isdir(os.path.join(path, ".git")):
        return path

    raise FileNotFoundError("Git root not found.")


def extract_json_block(text: str) -> str:
    """
    Extract JSON object from a string possibly wrapped in markdown-style backticks.
    """
    if not text:
        raise ValueError("Empty response")

    # Extract JSON inside triple backticks (```json ... ```)
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if match:
        return match.group(1)

    text = text.strip()
    if text.startswith("{") and text.endswith("}"):
        return text

    raise ValueError("No valid JSON found in response")


def sanitize_backslash(name: str) -> str:
    """Replace any character that's not alphanumeric, underscore, or hyphen with '-'"""
    return re.sub(r"[^a-zA-Z0-9_\-]", "-", name)


def approximate_token_count_char(text: str) -> int:
    """Approximates tokens based on character count - 4 chars per token."""
    return int(len(text) / 4)


def cvt_yml_to_json(content: str, file_path: str) -> str:
    chunks = []
    try:
        yml = yaml.safe_load(content)
        yml_json = json.dumps(yml, indent=2)
        return yml_json
    except:
        print("Error converting yaml file to json: ", file_path)
    return chunks


def generate_yml_string(content: str, file_path: str, parent_key: str = ""):
    json_content = json.loads(content)
    collection = []

    if isinstance(json_content, list):
        json_content = json_content[0]

    for key, item in json_content.items():
        current_key = f"{parent_key}.{key}" if parent_key else key
        if isinstance(item, dict):
            collection.extend(generate_yml_string(json.dumps(item), file_path, current_key))
        else:
            collection.append(f"{current_key}: {item}")
    return collection
