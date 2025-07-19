from website.aibot.clients import qdrant_client

source_collection = "repo_embeddings"
k = 15

import numpy as np

vector_query = np.random.uniform(low=-1.0, high=1.0, size=768)


main_points = qdrant_client.query_points(
    collection_name=source_collection, query=vector_query, limit=k, with_payload=True
)

for point in main_points.points:
    print(f"File: {point.payload['file_path']}")
    print(f"Line: {point.payload['start_line']}–{point.payload['end_line']}")
    print(f"Chunk:\n{point.payload['chunk']}\n")
    print(f"Score: {point.score}\n")
    break
