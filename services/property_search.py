from qdrant_client import QdrantClient
from embeddings import model
import numpy as np

def retrieve_properties(state: dict):
    locations = state.get("location", [])  # Now an array
    activities = state.get("activities", [])
    user_query = state.get("user_query", "").strip()

    # # Combine multiple locations into a single string
    location_text = " ".join(locations) if locations else ""
    activities_text = " ".join(activities) if activities else ""

    # # Compute embeddings separately
    # location_vector = model.encode(location_text).tolist() if location_text else np.zeros(384).tolist()
    # activities_vector = model.encode(activities_text).tolist() if activities_text else np.zeros(384).tolist()

    # # Weighted combination of vectors
    # query_vector = np.array(location_vector) * 0.7 + np.array(activities_vector) * 0.3
    # query_vector = query_vector.tolist()

    # query = f"Location:{' '.join(state.get('location', []))} Activities:{', '.join(state.get('activities', []))}".strip()

    query_vector = model.encode(user_query).tolist() if user_query else np.zeros(384).tolist()
    location_vector = model.encode(location_text).tolist() if location_text else np.zeros(384).tolist()
    activities_vector = model.encode(activities_text).tolist() if activities_text else np.zeros(384).tolist()
    combined_vector = (
        np.array(query_vector) * 0.3 + 
        np.array(location_vector) * 0.5 + 
        np.array(activities_vector) * 0.2
    ).tolist()
    # Compute query embedding
    # query_vector = model.encode(query).tolist() if query else np.zeros(384).tolist()

    client = QdrantClient("localhost", port=6333)

    # Create filter for matching locations in "country" or "region" fields
    location_filter = {
        "must": [
            {
                "should": [
                    {"key": "country", "match": {"value": loc}} for loc in state.get("location", [])
                ] + [
                    {"key": "region", "match": {"value": loc}} for loc in state.get("location", [])
                ]
            }
        ]
    } if state.get("location") else {}

    results = client.query_points(
        collection_name="postcard",
        # query=query_vector,
        query=combined_vector,
        limit=10,
        with_payload=True,
        query_filter=location_filter  # Apply filter
    )


    print("Query:", locations, activities)  # Debugging output
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
