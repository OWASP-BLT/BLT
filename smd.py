from typing import List

from langchain.text_splitter import RecursiveCharacterTextSplitter

from parse_utils import ChunkType

file_path = "sample.txt"

with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()


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


chunks = chunk_text_file(content, file_path)

for chunk in chunks:
    print(chunk["chunk"])
    print("-" * 40)
    print()
