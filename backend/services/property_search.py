from services.hotel import generate_embedding, cosine_similarity
from config.settings import qdrant
import numpy as np
import random
import time
# ------- Stage Filter Definitions -------
PRIORITY_CHAIN = {
    "properties": ["property", "activity", "postcard", "location"],
    "activities": ["activity", "postcard", "location", "property"],
    "location": ["location", "activity", "postcard" , "property"],
    "postcards": ["postcard", "activity", "location", "property"],
}

SEARCH_FIELDS = {
    "property": ["name", "intro"],
    "activity": ["activities"],
    "location": ["country", "region", "intro"],
    "postcard": ["name", "intro", "story"],
}

# ------- Top-K Selector -------
def top_k(candidates, scores, k):
    paired = list(zip(candidates, scores))
    paired.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in paired[:k]]

def retrieve_properties(state: dict):
    start_time = time.time()  
    locations = state.get("location", [])
    activities = state.get("activities", [])
    user_query = state.get("user_query", "").strip()
    priority = state.get("priority_field", "properties")
    months = state.get("months", [])  

    print("🔵 Priority selected by user:", priority)
    print("📍 Extracted Locations:", locations)
    print("🎯 Extracted Activities:", activities)
    print("📅 Extracted Months:", months)
    print("💬 User Query:", user_query)

    query_vector = generate_embedding(user_query) if user_query else np.zeros(768).tolist()

    # ----------- Qdrant Search -----------
    results = qdrant.query_points(
        collection_name="postcard",
        query=query_vector,
        limit=50,
        with_payload=True
    )

    # ----------- Initial Candidate Extraction -----------
    candidates = []
    for _, hits in results:
        for point in hits:
            candidates.append(point.payload)

    print(f"✅ Initial candidates fetched: {len(candidates)}")
    last_valid_candidates = candidates.copy()

     # ----------- Seasonal Filter ----------- 
    if months:
        candidates = [
            c for c in candidates if any(
                month.lower() in (c.get("bestTimetoTravel", "").lower())
                for month in months
            )
        ]
        print(f"⛅ Filtered by best_time_to_travel ➤ {len(candidates)}")
        last_valid_candidates = candidates.copy()

    # ----------- Multi-stage Filtering -----------
    threshold = 1
    time.sleep(0.5)  # Simulate processing time
    print("\n🔄 Multi-stage filtering process started...")
    for stage in PRIORITY_CHAIN[priority]:
        print(f"\n➡️ Applying filter for: {stage.upper()}")

        # Always apply on last valid candidates
        candidates = last_valid_candidates.copy()

        before_count = len(candidates)

        sims = []

        if stage == "property" and user_query:
            sims = [
                max([cosine_similarity(query_vector, generate_embedding(c.get(field, ""))) for field in SEARCH_FIELDS["property"]])
                for c in candidates
            ]
            candidates = top_k(candidates, sims, 3)

        elif stage == "activity":
            matched_activity_labels = [a[0].lower() for a in state.get("matched_activities", []) if a[1] >= 0.6]

            print("🔍 Matched Activity Labels:", matched_activity_labels)

            candidates = [
                c for c in candidates if any(
                    act.lower() in matched_activity_labels for act in c.get("activities", [])
                )
            ]

        elif stage == "postcard" and user_query:
            sims = [
                max([cosine_similarity(query_vector, generate_embedding(p.get(field, ""))) for p in c.get("postcards", []) for field in SEARCH_FIELDS["postcard"]], default=0)
                for c in candidates
            ]
            candidates = top_k(candidates, sims, 20)

       
        elif stage == "location":
            if not locations:
                print("⚠️ No locations given, skipping to 0 results.")
                candidates = []  # Force zero results
            else:
                candidates = [c for c in candidates if any(
                    loc.lower() in [(c.get("country") or "").lower(), (c.get("region") or "").lower(), (c.get("intro") or "").lower()]
                    for loc in locations
                )]

        print(f"🔸 Candidates reduced: {before_count} ➤ {len(candidates)}")

        if len(candidates) < threshold:
            print("⚠️ Not enough candidates in this stage. Trying next priority...")
            continue  # go to next stage without breaking
        else:
            last_valid_candidates = candidates.copy()

         # ----------- Fallback Case -----------

    if len(last_valid_candidates) < threshold:
            print("⚡ Fallback triggered: Selecting random 5 from initial search space")
            last_valid_candidates = random.sample(candidates if candidates else candidates + last_valid_candidates, min(5, len(candidates or last_valid_candidates)))

    print(f"\n🏁 Final candidates after filtering: {len(candidates)}\n")
    
    end_time = time.time()
    print(f"retrieve_properties execution time: {end_time - start_time:.2f} seconds")

    return {
        **state,
        "search_results": candidates,
        "need_more_input": False
    }
