from typing import TypedDict


class ChunkType(TypedDict, total=False):
    """Represents a chunk of code extracted from code files."""

    type: str
    name: str
    chunk: str
    file: str
    start_line: int
    end_line: int
    part_index: int
    part_total: int
