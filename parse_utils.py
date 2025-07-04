import ast
import logging
from typing import Dict, List, Set, Tuple, Union

ChunkType = Dict[str, Union[str, int, None]]


logger = logging.getLogger(__name__)


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
