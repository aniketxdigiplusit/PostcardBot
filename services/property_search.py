from qdrant_client import QdrantClient
from models.embeddings import model

def retrieve_properties(state: dict):
    query = f"{state.get('location', '')} {', '.join(state.get('activities', []))}".strip()

    client = QdrantClient("localhost", port=6333)
    query_vector = model.encode(query).tolist()

    results = client.query_points(
        collection_name="postcard",
        query=query_vector,
        limit=5,
        with_payload=True
    )

    state["search_results"] = [point.payload for _, hits in results for point in hits]
    return state
