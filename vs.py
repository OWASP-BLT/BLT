import os

import google.generativeai as genai
from qdrant_client import QdrantClient

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
embedding_model = "models/text-embedding-004"
qdrant_client = QdrantClient(host="qdrant", port=6333)

query = "which function is responsible for creating new issues in the website?"

response = genai.embed_content(
    model=embedding_model,
    content=query,
    task_type="retrieval_query",
)

embedding = response.get("embedding")

search_result = qdrant_client.query_points(
    collection_name="repo_embeddings",
    query=embedding,
    limit=5,
    with_payload=True,
)

for point in search_result.points:
    print("ID:", point.id)
    print("Score:", point.score)
    print("File Path:", point.payload["file_path"])
    print("Chunk:", point.payload["chunk"])
    print("Start Line:", point.payload["start_line"])
    print("End Line:", point.payload["end_line"])
    print("---")
