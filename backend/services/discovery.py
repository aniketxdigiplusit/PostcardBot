import json
import requests
from typing import List, Dict
from utils.helpers import send_to_llm
from config.settings import qdrant
from services.hotel import generate_embedding, cosine_similarity

def discovery_flow(state: dict):
    """
    Special conversational flow when priority is not selected.
    It asks questions and iteratively refines suggestions.
    """
    user_query = state.get("user_query", "")
    preferences = {
        "location": state.get("location", []),
        "activities": state.get("activities", []),
        "months": state.get("months", []),
        "prices": state.get("prices", [])
    }

    search_results = basic_property_search(preferences)  # 🔥 We'll build this next

    prompt = f"""
You are a friendly travel assistant from postcard travel club helping a user plan a dream trip.

Based on their current preferences: {preferences}

You have found these properties:
{json.dumps(search_results, indent=2)}

### Your Instructions:
- List 2-3 matching properties (name, intro, location).
- Be friendly and conversational, not formal.
- After suggesting, ask a helpful follow-up question:
    e.g., "Would you prefer something near beaches or mountains?", or
    "What's your ideal travel month?".
- Encourage users to tell you more, don't hard close.
-Dont ask things already filled in preferences
"""

    response = send_to_llm(prompt)

    return {**state, "chatbot_response": response}

def basic_property_search(preferences):
    """
    Lightweight semantic search across location, activities, best time to travel, and price.
    Results are ranked by relevance, not strict matching.
    """
    print("🔍 Searching for properties based on user preferences...")

    location_prefs = preferences.get("location", [])
    activity_prefs = preferences.get("activities", [])
    month_prefs = preferences.get("months", [])
    price_prefs = preferences.get("prices", [])

    if not (location_prefs or activity_prefs or month_prefs or price_prefs):
        return []

    points, _ = qdrant.scroll(
        collection_name="postcard-openai",
        scroll_filter=None,
        with_payload=True,
        limit=300,
        with_vectors=False,
    )

    # Precompute user preference embeddings
    user_location_embedding = generate_embedding(" ".join(location_prefs)) if location_prefs else None
    user_activity_embedding = generate_embedding(" ".join(activity_prefs)) if activity_prefs else None
    user_month_embedding = generate_embedding(" ".join(month_prefs)) if month_prefs else None

    candidates = []

    for point in points:
        payload = point.payload
        score = 0.0

        # --- Location matching ---
        prop_location = (payload.get("region", "") + " " + payload.get("country", "")).strip()
        if prop_location and user_location_embedding:
            location_embedding = generate_embedding(prop_location)
            loc_score = cosine_similarity(location_embedding, user_location_embedding)
            score += loc_score * 0.4  # location weight

        # --- Activities matching ---
        prop_activities = payload.get("activities", [])
        if prop_activities and user_activity_embedding:
            act_text = " ".join(prop_activities)
            act_embedding = generate_embedding(act_text)
            act_score = cosine_similarity(act_embedding, user_activity_embedding)
            score += act_score * 0.3  # activities weight

        # --- Best Time to Travel matching ---
        prop_best_time = payload.get("bestTimetoTravel", "")
        if prop_best_time and user_month_embedding:
            best_time_embedding = generate_embedding(prop_best_time)
            month_score = cosine_similarity(best_time_embedding, user_month_embedding)
            score += month_score * 0.2  # month weight

        # --- Price matching (simple range check) ---
        prop_price = payload.get("price")
        if prop_price and price_prefs:
            try:
                # assume user provided a rough number (e.g., "200", "3000")
                user_budget = max(price_prefs)
                # Closer price gets more points (simple inverse diff)
                price_score = max(0, 1 - abs(prop_price - user_budget) / user_budget)
                score += price_score * 0.1  # small price influence
            except Exception as e:
                pass  # price missing or non-numeric, ignore

        candidates.append({
            "payload": payload,
            "score": score
        })

    # Sort by total score
    candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)
    print("🔝 Top candidates found:", len(candidates))

    # Pick top 5 results
    results = []
    for c in candidates[:5]:
        payload = c["payload"]
        results.append({
            "name": payload.get("name", ""),
            "intro": payload.get("intro", ""),
            "region": payload.get("region", ""),
            "country": payload.get("country", ""),
            "activities": payload.get("activities", []),
            "bestTimetoTravel": payload.get("bestTimetoTravel", ""),
            "price": payload.get("price", "")
        })
        print(f"🏨 Found property: {payload.get('name', '')} in {payload.get('region', '')}, {payload.get('country', '')} with score: {c['score']:.2f}")

    return results
