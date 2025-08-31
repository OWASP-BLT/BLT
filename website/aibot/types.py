from enum import Enum
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


class EmbeddingTaskType(Enum):
    SEMANTIC_SIMILARITY = "SEMANTIC_SIMILARITY"
    RETRIEVAL_QUERY = "RETRIEVAL_QUERY"
    RETRIEVAL_DOCUMENT = "RETRIEVAL_DOCUMENT"
    CLASSIFICATION = "CLASSIFICATION"
    CLUSTERING = "CLUSTERING"
