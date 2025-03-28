from qdrant_client import QdrantClient
from embeddings import model
import numpy as np

def retrieve_properties(state: dict):
    location = state.get("location", "").strip()
    activities = state.get("activities", [])
    
    # Compute embeddings separately
    location_vector = model.encode(location).tolist() if location else np.zeros(384).tolist()
    activities_vector = model.encode(" ".join(activities)).tolist() if activities else np.zeros(384).tolist()

    # Weighted combination of vectors
    query_vector = np.array(location_vector) * 0.7 + np.array(activities_vector) * 0.3
    query_vector = query_vector.tolist()

    client = QdrantClient("localhost", port=6333)

    results = client.query_points(
        collection_name="postcard",
        query=query_vector,
        limit=10,
        with_payload=True
    )

    print("Query:", location, activities)
    res = []
    for _, hits in results:
        for point in hits:
            payload = point.payload.copy()  # Copy payload to avoid modifying original data
            res.append(payload)

    return {
        **state,
        "search_results": res,
        "need_more_input": False
    }
