from qdrant_client import QdrantClient
from services.hotel import generate_embedding
import numpy as np

def retrieve_properties(state: dict):
    location = state.get("location", "").strip()
    activities = state.get("activities", [])

    # ✅ Compute embeddings via Ollama
    location_vector = generate_embedding(location) if location else np.zeros(768).tolist()
    activities_vector = generate_embedding(" ".join(activities)) if activities else np.zeros(768).tolist()

    # ✅ Weighted combination
    query_vector = np.array(location_vector) * 0.7 + np.array(activities_vector) * 0.3
    query_vector = query_vector.tolist()

    client = QdrantClient("localhost", port=6333)

    # ✅ Qdrant search
    results = client.search(
        collection_name="postcard",
        query_vector=query_vector,
        limit=10,
        with_payload=True
    )

    print("Query:", location, activities)

    res = []
    for point in results:
        payload = point.payload.copy()
        res.append(payload)

    return {
        **state,
        "search_results": res,
        "need_more_input": False
    }