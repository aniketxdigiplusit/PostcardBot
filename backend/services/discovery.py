import json
import requests
from typing import List, Dict
from utils.helpers import send_to_llm, send_to_llm
from config.settings import qdrant
from services.hotel import generate_embedding, cosine_similarity
from services.chat_db import get_chat_messages
from services.entity_extraction import normalize_entities
from config.db import save_preferences, get_preferences
from services.followup import generate_followups_from_response

# def discovery_flow(state: dict):
#     """
#     Special conversational flow when priority is not selected.
#     It asks questions and iteratively refines suggestions.
#     """
#     user_query = state.get("user_query", "")
#     preferences = {
#         "location": state.get("location", []),
#         "activities": state.get("activities", []),
#         "months": state.get("months", []),
#         "prices": state.get("prices", [])
#     }

#     search_results = basic_property_search(preferences)  # 🔥 We'll build this next

#     prompt = f"""
# You are a friendly travel assistant from postcard travel club helping a user plan a dream trip.

# Based on their current preferences: {preferences}

# You have found these properties:
# {json.dumps(search_results, indent=2)}

# ### Your Instructions:
# - List 2-3 matching properties (name, intro, location).
# - Be friendly and conversational, not formal.
# - After suggesting, ask a helpful follow-up question:
#     e.g., "Would you prefer something near beaches or mountains?", or
#     "What's your ideal travel month?".
# - Encourage users to tell you more, don't hard close.
# -Dont ask things already filled in preferences
# """

#     response = send_to_llm(prompt)

#     return {**state, "chatbot_response": response}

def get_last_messages(thread_id, limit=4):
    messages = get_chat_messages(thread_id, limit=limit)
    messages = list(reversed(messages))
    formatted = ""
    for idx, m in enumerate(messages, start=1):
        sender = m["sender"]
        text = m["text"]
        formatted += f"{sender.title()}: {text}\n"
    return formatted.strip()

def start_discovery_flow(state: dict):
    """
    Triggered when priority is not set but some preferences exist.
    This is the entry into the 'discovery' path.
    The chatbot will guide the user to share remaining preferences in a conversational tone.
    """
    state["discovery_mode"] = True
    state["missing_fields"] = []
    print("🔍 Starting discovery flow...")

    preferences = {
        "location": state.get("location", []),
        "activities": state.get("activities", []),
        "months": state.get("months", []),
        "prices": state.get("prices", [])
    }

    for key, value in preferences.items():
        if not value:
            state["missing_fields"].append(key)

    history = get_last_messages(state.get("thread_id", ""))

    if state["missing_fields"]:
        next_field = state["missing_fields"].pop(0)

        # ✨ Improved, specific LLM prompt
        prompt = f"""
You are a helpful travel assistant guiding a user through a conversational discovery journey on Postcard Travel – a platform for conscious luxury travelers.

Here’s the recent conversation:
{history}

From the conversation so far, the user has shared some preferences (like destination or interests) but hasn't selected a specific priority (like properties, activities, or locations).

Your task:
1. Politely acknowledge the preferences they've already mentioned.
2. Naturally ask for their **{next_field}** preference in a conversational tone.
   - If it's `months`, ask: *"When are you thinking of traveling?"*
   - If it's `prices`, ask: *"What kind of budget or price range are you comfortable with?"*
   - If it's `activities`, ask: *"What kind of experiences or activities are you hoping to enjoy?"*
   - If it's `location`, ask: *"Any specific place you’d love to visit or explore?"*
3. Be friendly, not robotic. Don’t list options, just ask the question smoothly based on the context.
4. Make the user feel like you’re personally helping plan something meaningful.

Return only the follow-up message to show the user.
        """

        response = send_to_llm(prompt)
        return {
            **state,
            "followup": response.strip(),
            "need_more_input": True
        }

    # If no missing fields, move on to continue the discovery process
    return continue_discovery_flow(state)


def continue_discovery_flow(state: dict):
    """
    Continue collecting missing preferences from the user in discovery mode.
    No re-normalization — uses existing state passed from LangGraph.
    """
    print("🔍 Continuing discovery flow...")
    
    preferences = {
        "location": state.get("location", []),
        "activities": state.get("activities", []),
        "months": state.get("months", []),
        "prices": state.get("prices", [])
    }

    missing = [k for k, v in preferences.items() if not v]
    state["missing_fields"] = missing

    history = get_last_messages(state.get("thread_id", ""))
    print(f"history: {history}")

    user_query = state.get("user_query", "")

    if missing:
        next_field = missing[0]
        prompt = f"""
You are a friendly travel assistant at Postcard Travel Club.

The user is in the middle of sharing their preferences to plan a trip. Here's the recent chat:

{history}

This is the current query:
{user_query}

Preferences so far:
{json.dumps(preferences, indent=2)}

They've already provided some info. Now ask them about their **{next_field}** preference in a natural, helpful tone.
Use soft language, for example:
- "What kind of activities are you hoping to include?"
- "Do you have a budget in mind?"
- "Which months are ideal for your trip?"

Do not repeat what was already said. Ask just one thing at a time.
"""
        response = send_to_llm(prompt)
        followups = generate_followups_from_response(response, [], state.get("user_query", ""))
        return {
            **state,
            "chatbot_response": response.strip(),
            "need_more_input": False,
            "ready_to_resolve_priority": True,
            "followups": followups

        }

    return resolve_discovery_priority(state)


def resolve_discovery_priority(state: dict):
    """
    Ask user for their top preference (priority) after all fields are collected.
    """
    print("🔍 Resolving discovery priority...")

    history = get_last_messages(state.get("thread_id", ""))
    prompt = f"""
You're a helpful assistant planning a trip with the user. You've collected their preferences (destination, time, price, etc.).

Now you need to help them decide what matters most *right now*.

Here’s the recent conversation:
{history}

Kindly ask them:
"What’s most important to you at this moment – location, activities, travel time, or budget?"

Keep your tone warm and curious. Don’t repeat what’s already known. Return only the question.
"""
    response = send_to_llm(prompt)
    followups = generate_followups_from_response(response, [], state.get("user_query", ""))
    thread_id = state.get("thread_id")
    prefs = get_preferences(thread_id) or {}
    location = prefs.get("location", [])
    activities = prefs.get("activities", [])
    months = prefs.get("months", [])
    prices = prefs.get("prices", [])
    resolved_priority= prefs.get("resolved_priority", None)
    # ✅ Mark that we've already asked
    save_preferences(
        thread_id=thread_id,
        location=location,
        activities=activities,
        months=months,
        prices=prices,
        resolved_priority=resolved_priority,
        asked_resolve_priority=True
)

    return {
        **state,
        "chatbot_response": response.strip(),
        "need_more_input": True, 
        "followups": followups,
    }

def extract_resolved_priority(state: dict):
    """
    Uses LLM to extract what the user cares about most: location, activities, time, or budget.
    """
    user_query = state.get("user_query", "")
    print("🔍 Extracting resolved priority...")
    prompt = f"""
You are helping extract the user's top priority for planning their travel.

They just said: "{user_query}"

Pick one of the following values as the most important to the user right now:
- location
- activities
- months
- prices

Only output one of the above values. No explanation.
"""
    priority = send_to_llm(prompt).strip().lower()

    if priority not in ["location", "activities", "months", "prices"]:
        priority = "location"  

    thread_id = state.get("thread_id")
    prefs = get_preferences(thread_id) or {}
    location = prefs.get("location", [])
    activities = prefs.get("activities", [])
    months = prefs.get("months", [])
    prices = prefs.get("prices", [])
    asked_resolve_priority=prefs.get("asked_resolve_priority", False)

    # Save to DB or state
    save_preferences(
        thread_id=state.get("thread_id"),
        location=location,
        activities=activities,
        months=months,
        prices=prices,
        resolved_priority=priority,
        asked_resolve_priority=asked_resolve_priority
    )
    followups = generate_followups_from_response(priority, [], state.get("user_query", ""))

    return {
        **state,
        "resolved_priority": priority,
        "followup": followups,
    }

def basic_property_search(preferences, resolved_priority=None):
    """
    Semantic search using soft scoring based on resolved priority.
    Supports: location, activities, months (travel time), prices.
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

    # Embeddings
    user_location_embedding = generate_embedding(" ".join([loc[0] for loc in location_prefs])) if location_prefs else None

    user_activity_embedding = generate_embedding(" ".join([act[0] for act in activity_prefs])) if activity_prefs else None

    user_month_embedding = generate_embedding(" ".join(map(str, month_prefs))) if month_prefs else None


    # 🔧 Set dynamic weights
    weights = {
        "location": 0.3,
        "activities": 0.3,
        "months": 0.2,
        "prices": 0.2
    }

    # Prioritize the resolved_priority more heavily
    if resolved_priority in weights:
        for key in weights:
            weights[key] = 0.2  # spread default
        weights[resolved_priority] = 0.8 # boost selected priority

    candidates = []

    for point in points:
        payload = point.payload
        score = 0.0

        # --- Location matching ---
        prop_location = (payload.get("region", "") + " " + payload.get("country", "")).strip()
        if prop_location and user_location_embedding:
            location_embedding = generate_embedding(prop_location)
            loc_score = cosine_similarity(location_embedding, user_location_embedding)
            score += loc_score * weights["location"]

        # --- Activities matching ---
        prop_activities = payload.get("activities", [])
        if prop_activities and user_activity_embedding:
            act_text = " ".join(prop_activities)
            act_embedding = generate_embedding(act_text)
            act_score = cosine_similarity(act_embedding, user_activity_embedding)
            score += act_score * weights["activities"]

        # --- Months matching ---
        prop_best_time = payload.get("bestTimetoTravel", "")
        if prop_best_time and user_month_embedding:
            best_time_embedding = generate_embedding(prop_best_time)
            month_score = cosine_similarity(best_time_embedding, user_month_embedding)
            score += month_score * weights["months"]

        # --- Price matching ---
        prop_price = payload.get("price")
        if prop_price and price_prefs:
            try:
                user_budget = max(price_prefs)
                price_score = max(0, 1 - abs(prop_price - user_budget) / user_budget)
                score += price_score * weights["prices"]
            except Exception as e:
                print(f"⚠️ Price matching error: {e}")

        candidates.append({
            "payload": payload,
            "score": score
        })

    candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)
    print(f"🔝 Top {len(candidates)} candidates ranked by score")

    # Top 5 only
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
        print(f"🏨 {payload.get('name')} — {payload.get('region')}, {payload.get('country')} | score: {c['score']:.2f}")

    return results


def retrieve_discovery_properties(state: dict):
    print("🌿 Running discovery-based property search...")

    preferences = {
        "location": state.get("location", []),
        "activities": state.get("activities", []),
        "months": state.get("months", []),
        "prices": state.get("prices", [])
    }

    resolved_priority = state.get("resolved_priority", None)
    results = basic_property_search(preferences, resolved_priority=resolved_priority)

    return {
        **state,
        "search_results": results
    }
