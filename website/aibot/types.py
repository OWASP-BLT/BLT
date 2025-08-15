from typing import TypedDict


class ChunkType(TypedDict, total=False):
    """Represents a chunk of code extracted from code files."""

    file_name: str
    file_path: str
    file_ext: str
    chunk_type: str
    content: str
    start_line: int
    end_line: int
    part_index: int
    part_total: int
