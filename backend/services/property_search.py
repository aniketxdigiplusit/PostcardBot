from services.hotel import generate_embedding, cosine_similarity
from config.settings import qdrant
from utils.helpers import send_to_openai, send_to_openai
from config.db import get_preferences
import numpy as np
import random
import time
# ------- Stage Filter Definitions -------
PRIORITY_CHAIN = {
    "properties": ["property", "location", "activity", "postcard"],
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


def rewrite_query_with_preferences(user_query, prefs):
    preference_summary = []
    if prefs.get("location"):
        preference_summary.append(f"location: {prefs['location']}")
    if prefs.get("activities"):
        acts = ", ".join(prefs['activities'])
        preference_summary.append(f"activities: {acts}")
    if prefs.get("months"):
        preference_summary.append(f"time to travel: {', '.join(prefs['months'])}")
    if prefs.get("prices"):
        preference_summary.append(f"budget: {', '.join(map(str, prefs['prices']))}")

    new_prompt = (
        f"User query: {user_query}\n\nPreferences: {', '.join(preference_summary)}\n\n"
        f"Rewrite the query to include preferences clearly without losing the user's original intent. Write in one line"
    )

    response = send_to_openai(new_prompt)
    rewritten_query = response.strip()
    print("📝 Rewritten Query:", rewritten_query)


    return rewritten_query
def retrieve_properties(state: dict):
    print("🚨 retrieve_properties() is being called 🚨")
    start_time = time.time()  
    thread_id = state.get("thread_id")
    priority= state.get("priority_field", "properties") 
    prefs = get_preferences(thread_id) or {}

    locations = [prefs.get("location")] if prefs.get("location") else []
    activities = prefs.get("activities", [])
    months = prefs.get("months", [])
    prices = prefs.get("prices", [])
    resolved_priority = prefs.get("resolved_priority") or state.get("priority_field", "properties")

    user_query = rewrite_query_with_preferences(state.get("user_query", ""), prefs)
    print("🔄 Rewritten Query:", user_query)

    print("🔵 Priority selected by user:", resolved_priority)
    print("📍 DB Locations:", locations)
    print("🎯 DB Activities:", activities)
    print("📅 DB Months:", months)
    print("💰 DB Prices:", prices)
    print("resolved_priority:", resolved_priority)

    query_vector = generate_embedding(user_query) if user_query else np.zeros(768).tolist()

    # ----------- Qdrant Search -----------
    results = qdrant.query_points(
        collection_name="postcard-openai",
        query=query_vector,
        limit=250,
        # using="activity_vector",
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
    if resolved_priority == "travel_time" and months:
        seasonal_candidates = [
            c for c in candidates if any(
                month.lower() in (c.get("bestTimetoTravel", "").lower())
                for month in months
            )
        ]
        print(f"⛅ Filtered by best_time_to_travel ➤ {len(seasonal_candidates)}")
        if seasonal_candidates:
            last_valid_candidates = seasonal_candidates  # ✅ Only replace if valid
        else:
            print("⚠️ Seasonal filter returned 0 — keeping previous candidates.")


    # ----------- Multi-stage Filtering -----------
    threshold = 1
    # time.sleep(0.5)  # Simulate processing time
    print("\n🔄 Multi-stage filtering process started...")
    for stage in PRIORITY_CHAIN[priority]:
        print(f"\n➡️ Applying filter for: {stage.upper()}")

        # Always apply on last valid candidates
        candidates = last_valid_candidates.copy()

        before_count = len(candidates)

        sims = []
        if stage == "property" and user_query:
    # Retrieve precomputed embeddings for properties from Qdrant
            sims = [
                max([cosine_similarity(query_vector, c.get("embedding_name", [])) for field in SEARCH_FIELDS["property"]])
                for c in candidates
            ]
            candidates = top_k(candidates, sims, 10)
            print("🔍 Matched Property Labels:", [c.get("name") for c in candidates])


        elif stage == "activity":
            matched_activity_labels = [a[0].lower() for a in state.get("matched_activities", []) if a[1] >= 0.6]

            print("🔍 Matched Activity Labels:", matched_activity_labels)

            candidates = [
                c for c in candidates if any(
                    act.lower() in matched_activity_labels for act in c.get("activities", [])
                )
            ]

        elif stage == "postcard" and user_query:
    # Retrieve precomputed embeddings for postcards from Qdrant
            sims = [
                max([cosine_similarity(query_vector, c.get("embedding_postcards", [])) for p in c.get("postcards", [])], default=0)
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

    
    if resolved_priority != "travel_time" and months:
        post_seasonal = [
            c for c in last_valid_candidates if any(
                month.lower() in (c.get("bestTimetoTravel", "").lower())
                for month in months
            )
        ]
        print(f"⛅ Applied best_time_to_travel at end ➤ {len(post_seasonal)}")
        if post_seasonal:
            last_valid_candidates = post_seasonal  # ✅ Only update if valid
        else:
            print("⚠️ Post-stage seasonal filter returned 0 — keeping previous results.")


         # ----------- Fallback Case -----------

    if len(last_valid_candidates) < threshold:
            print("⚡ Fallback triggered: Selecting random 5 from initial search space")
            last_valid_candidates = random.sample(candidates if candidates else candidates + last_valid_candidates, min(5, len(candidates or last_valid_candidates)))

    print(f"\n🏁 Final candidates after filtering: {len(last_valid_candidates)}\n")
    
    end_time = time.time()
    print(f"retrieve_properties execution time: {end_time - start_time:.2f} seconds")

    return {
        **state,
        "search_results": last_valid_candidates[:3], 
        "need_more_input": False
    } 