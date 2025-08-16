import ast
import json
import logging
import math
import os
from collections import defaultdict
from typing import List, Set, Tuple

import yaml
from langchain.text_splitter import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from website.aibot.types import ChunkType
from website.aibot.utils import approximate_token_count_char

logger = logging.getLogger(__name__)


MAX_TOKENS = 1500
OVERLAP_LINES = 7
CHUNK_OVERLAP = 200
CHUNK_SIZE = 1000


import math
from typing import List


def _split_chunk_lines(
    chunk: ChunkType, total_tokens: int, max_tokens: int = MAX_TOKENS, overlap: int = OVERLAP_LINES
) -> List[ChunkType]:
    """Returns a list of smaller, overlapping chunks."""
    code_lines = chunk["content"].splitlines(keepends=True)
    n_parts = math.ceil(total_tokens / max_tokens)
    total_code_lines = len(code_lines)
    lines_per_part = math.ceil(total_code_lines / n_parts)
    mini_chunks: List[ChunkType] = []

    for part_idx in range(n_parts):
        start_idx = part_idx * lines_per_part

        if part_idx != 0:
            start_idx -= overlap
        end_idx = min(start_idx + lines_per_part + overlap, total_code_lines)
        snippet = "".join(code_lines[start_idx:end_idx])

        if not snippet.strip():
            continue

        mini_chunks.append(
            ChunkType(
                file_name=chunk["file_name"],
                file_path=chunk["file_path"],
                file_ext=chunk["file_ext"],
                chunk_type=chunk["chunk_type"],
                content=snippet,
                start_line=chunk["start_line"] + start_idx + 1,
                end_line=chunk["start_line"] + end_idx,
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
        if not chunk["content"].strip():
            continue

        token_count = approximate_token_count_char(chunk["content"])

        if token_count <= MAX_TOKENS:
            processed_chunks.append(chunk)
        else:
            processed_chunks.extend(_split_chunk_lines(chunk, token_count))

    return processed_chunks


def chunk_file(content: str, file_path: str) -> List[ChunkType]:
    """Delegates to appropriate chunker based on file type, defaults to chunk_text_file."""
    file_path_lower = file_path.lower()
    file_name = os.path.basename(file_path_lower)

    chunkers = {
        "settings.py": chunk_settings_file,
        "urls.py": chunk_urls_file,
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
            logger.info("Chunking file: %s", file_path)
            return chunker(content, file_path)

    logger.info("No specific chunker matched for file: %s, using default text chunker", file_path)
    return chunk_text_file(content, file_path)


def cvt_yml_to_json(content: str, file_path: str) -> str:
    try:
        yml = yaml.safe_load(content)
        yml_json = json.dumps(yml, indent=2)
        return yml_json
    except:
        print("Error converting yaml file to json: ", file_path)
    return ""


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


def chunk_text_file(
    content: str, file_path: str, chunk_size: int = CHUNK_SIZE, chunk_overlap: int = CHUNK_OVERLAP
) -> List[ChunkType]:
    splitter = RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n", ". ", " "],
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
    )

    chunks = splitter.split_text(content)
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_path)[1].lower()

    total_parts = len(chunks)

    return [
        ChunkType(
            file_name=file_name,
            file_path=file_path,
            file_ext=file_ext,
            chunk_type="text_paragraph",
            content=chunk,
            start_line=-1,
            end_line=-1,
            part_index=i,
            part_total=total_parts,
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
                file_name=os.path.basename(file_path),
                file_path=file_path,
                file_ext=os.path.splitext(file_path)[1].lower(),
                chunk_type="markdown_section",
                content=final_content,
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
                    ChunkType(
                        file_name=os.path.basename(file_path),
                        file_path=file_path,
                        file_ext=os.path.splitext(file_path)[1].lower(),
                        chunk_type="json_array_item",
                        content=json.dumps(item, indent=2),
                        start_line=-1,
                        end_line=-1,
                        part_index=idx + 1,
                        part_total=len(json_content),
                    )
                )
    elif isinstance(json_content, dict):
        items = list(json_content.items())
        values_are_objects = all(isinstance(v, dict) for v in json_content.values())

        if values_are_objects and len(json_content) > 0:
            # Case 2: Nested object like {"k1": {}, "k2": {}}
            for idx, (key, value) in enumerate(items):
                chunks.append(
                    ChunkType(
                        file_name=os.path.basename(file_path),
                        file_path=file_path,
                        file_ext=os.path.splitext(file_path)[1].lower(),
                        chunk_type="json_nested_object",
                        content=json.dumps(value, indent=2),
                        start_line=-1,
                        end_line=-1,
                        part_index=idx + 1,
                        part_total=len(items),
                    )
                )
        else:
            chunks.append(
                ChunkType(
                    file_name=os.path.basename(file_path),
                    file_path=file_path,
                    file_ext=os.path.splitext(file_path)[1].lower(),
                    chunk_type="json_full_object",
                    content=json.dumps(json_content, indent=2),
                    start_line=-1,
                    end_line=-1,
                    part_index=1,
                    part_total=1,
                )
            )
    else:
        pass

    return chunks


def chunk_yaml_file(content: str, file_path: str) -> List[ChunkType]:
    yml_json = cvt_yml_to_json(content, file_path)
    if not yml_json:
        return chunk_text_file(content, file_path)
    yml_string = generate_yml_string(yml_json, file_path)

    level_1_settings = []
    group_chunks = []
    groups = defaultdict(str)
    for line in yml_string:
        main_key, value = line.split(":", 1)
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
        file_name=os.path.basename(file_path),
        file_path=file_path,
        file_ext=os.path.splitext(file_path)[1].lower(),
        chunk_type="yaml",
        content=level_1_code,
        start_line=-1,
        end_line=-1,
        part_index=0,
        part_total=1,
    )
    group_chunks = []

    for group_name, group_content in groups.items():
        group_content = group_content.rstrip("\n")
        group_content = f"File: {file_path}\n {group_name}:\n{group_content}"
        group_chunk = ChunkType(
            file_name=os.path.basename(file_path),
            file_path=file_path,
            file_ext=os.path.splitext(file_path)[1].lower(),
            chunk_type="yaml",
            content=group_content,
            start_line=-1,
            end_line=-1,
            part_index=0,
            part_total=1,
        )
        group_chunks.append(group_chunk)

    return [level_1_chunk] + group_chunks


def chunk_html_file(content: str, file_path: str) -> List[ChunkType]:
    """As of now, there is no specific implementation for html files, though there is scope.
    So, it treats it as a normal text file and chunks recursively.
    """
    return chunk_text_file(content, file_path)


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
        logger.warning("Defaulting to basic text splitter for %s", file_path)
        return chunk_text_file(content, file_path)

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


def chunk_urls_file(content: str, file_path: str) -> List[ChunkType]:
    """
    Splits the contents of a URL-related file into overlapping text chunks.

    Args:
        content (str): The raw string content of the file to be chunked.
        file_path (str): Path to the original file, used for metadata or reference.

    Returns:
        List[ChunkType]: A list of processed text chunks, each containing
        a portion of the file with specified overlap for context preservation.

    Note:
        This function wraps `chunk_text_file` with fixed parameters:
        - chunk_size: 300 characters
        - chunk_overlap: 50 characters
    """
    chunk_size = 300
    chunk_overlap = 50
    return chunk_text_file(content, file_path, chunk_size, chunk_overlap)


def chunk_settings_file(content: str, file_path: str) -> List[ChunkType]:
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
                ChunkType(
                    file_name=os.path.basename(file_path),
                    file_path=file_path,
                    file_ext=os.path.splitext(file_path)[1].lower(),
                    chunk_type="class" if isinstance(node, ast.ClassDef) else "function",
                    content=code_chunk,
                    start_line=start_line + 1,
                    end_line=end_line,
                    part_index=0,
                    part_total=1,
                )
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
    chunk = ChunkType(
        file_name=os.path.basename(file_path),
        file_path=file_path,
        file_ext=os.path.splitext(file_path)[1].lower(),
        chunk_type="import_block",
        content=code_chunk,
        start_line=start_line + 1,
        end_line=end_line,
    )

    return [chunk], covered_lines


def extract_module_level_code(lines: List[str], covered_lines: Set[int], file_path: str) -> List[ChunkType]:
    """
    Extract remaining top-level code that wasn't captured.
    """
    chunks: List[ChunkType] = []
    current_block = []
    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_path)[1].lower()

    def append_block(start_line: int, end_line: int, block_lines: List[str]):
        if not block_lines:
            return
        chunks.append(
            ChunkType(
                file_name=file_name,
                file_path=file_path,
                file_ext=file_ext,
                chunk_type="module-level-code",
                content="\n".join(block_lines),
                start_line=start_line,
                end_line=end_line,
            )
        )

    for i, line in enumerate(lines):
        if i in covered_lines:
            append_block(i - len(current_block) + 1, i, current_block)
            current_block = []
            continue

        if line.strip() == "":
            append_block(i - len(current_block) + 1, i, current_block)
            current_block = []
        else:
            current_block.append(line)

    if current_block:
        append_block(len(lines) - len(current_block) + 1, len(lines), current_block)

    return chunks


def extract_if_blocks(tree: ast.AST, lines: List[str], file_path: str) -> Tuple[List[ChunkType], Set[int]]:
    """
    Extract top-level if-blocks and return as chunks along with covered line numbers.
    """
    if_blocks: List[ChunkType] = []
    covered_lines = set()

    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_path)[1].lower()

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.If):
            start_line = node.lineno - 1
            end_line = node.end_lineno
            code = "\n".join(lines[start_line:end_line])
            covered_lines.update(range(start_line, end_line))

            if_blocks.append(
                ChunkType(
                    file_name=file_name,
                    file_path=file_path,
                    file_ext=file_ext,
                    chunk_type="if-block",
                    content=code,
                    start_line=start_line + 1,
                    end_line=end_line,
                )
            )

    return if_blocks, covered_lines


def extract_try_blocks(tree: ast.AST, lines: List[str], file_path: str) -> Tuple[List[ChunkType], Set[int]]:
    """
    Extract try-except blocks and return as chunks along with covered line numbers.
    """
    try_blocks: List[ChunkType] = []
    covered_lines = set()

    file_name = os.path.basename(file_path)
    file_ext = os.path.splitext(file_path)[1].lower()

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Try):
            start_line = node.lineno - 1
            end_line = node.end_lineno
            code = "\n".join(lines[start_line:end_line])
            covered_lines.update(range(start_line, end_line))

            try_blocks.append(
                ChunkType(
                    file_name=file_name,
                    file_path=file_path,
                    file_ext=file_ext,
                    chunk_type="try-block",
                    content=code,
                    start_line=start_line + 1,
                    end_line=end_line,
                )
            )

    return try_blocks, covered_lines
