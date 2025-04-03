from services.hotel import generate_embedding
from config.settings import qdrant
import numpy as np
import time

def retrieve_properties(state: dict):
    start_time = time.time()
    locations = state.get("location", [])  # Now an array
    activities = state.get("activities", [])
    user_query = state.get("user_query", "").strip()
    priority = state.get("priority_field", "")  
    print("Priority Field:", priority)  # Debugging output

    # # Combine multiple locations into a single string
    query_vector = generate_embedding(user_query) if user_query else np.zeros(768).tolist()
    location_vector = generate_embedding(" ".join(locations)) if locations else np.zeros(768).tolist()
    activities_vector = generate_embedding(" ".join(activities)) if activities else np.zeros(768).tolist()

    combined_vector = (
        np.array(query_vector) * 0.3 + 
        np.array(location_vector) * 0.5 + 
        np.array(activities_vector) * 0.2
    ).tolist()
 
    location_filter = {
        "must": [
            {
                "should": [
                    {"key": "country", "match": {"value": loc}} for loc in locations
                ] + [
                    {"key": "region", "match": {"value": loc}} for loc in locations
                ] + [
                    {"key": "activities", "match": {"value": act}} for act in activities
                ]
            }
        ]
    } if locations or activities else {}
    results = qdrant.query_points(
        collection_name="postcard",
        # query=query_vector,
        query=combined_vector,
        limit=50,
        with_payload=True,
        query_filter=location_filter  # Apply filter
    )
    
    # ---- Priority Weights ----
    WEIGHTS = {
        "location": 5.0 if priority == "location" else 1.0,
        "activities": 5.0 if priority == "activities" else 1.0,
        "postcards": 5.0 if priority == "postcards" else 1.0,
        "query": 1.0
    }

    ranked_results = []

    # ---- Ranking ----
    print("Query:", locations, activities)  # Debugging output
    for _, hits in results:
        for point in hits:
            payload = point.payload.copy()
            name_vector = generate_embedding(payload.get("name", ""))
            intro_vector = generate_embedding(payload.get("intro", ""))
            postcard_vector = generate_embedding(" ".join([p.get("intro", "") for p in payload.get("postcards", [])]))

            # Weighted similarity
            sim = (
                cosine_similarity(query_vector, name_vector) * WEIGHTS["query"] +
                cosine_similarity(location_vector, name_vector) * WEIGHTS["location"] +
                cosine_similarity(activities_vector, name_vector) * WEIGHTS["activities"] +
                cosine_similarity(query_vector, postcard_vector) * WEIGHTS["postcards"]
            )
            print(f"Similarity for {payload.get('name', '')}: {sim}")

            ranked_results.append({
                "payload": payload,
                "score": sim
            })

    # ---- Sort by Score ----
    ranked_results.sort(key=lambda x: x["score"], reverse=True)
    ranked_payloads = [r["payload"] for r in ranked_results[:5]]
    end_time = time.time()  
    print(f"retrieve_properties execution time: {end_time - start_time:.2f} seconds")


    return {
        **state,
        "search_results": ranked_payloads,
        "need_more_input": False
    }

def cosine_similarity(vec1, vec2):
    if not vec1 or not vec2:
        return 0.0
    vec1, vec2 = np.array(vec1), np.array(vec2)
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))