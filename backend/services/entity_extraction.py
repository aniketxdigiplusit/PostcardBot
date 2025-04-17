import json
import re
from services.chat_db import get_chat_messages
from langchain.schema import SystemMessage, HumanMessage
from langchain.prompts import PromptTemplate
from config.settings import sllm
from embeddings import semantic_match, location_labels, location_vectors, activity_labels, activity_vectors
from utils.helpers import system_prompt, send_to_llm, send_to_azure_openai
from services.hotel import generate_embedding
from config.db import  get_preferences, save_preferences

def chunk_text(text, chunk_size=3, overlap=2):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = words[start:end]
        if not chunk:
            break
        chunks.append(' '.join(chunk))
        start = end - overlap
    return chunks


def normalize_entities(state: dict):
    thread_id = state.get("thread_id")
    print(f"Thread ID: {thread_id}")
    messages = get_chat_messages(thread_id, limit=6)
    last_2 = messages[:2] if len(messages) > 6 else messages
    print(f"Last 2 messages: {last_2}")  # Debugging line
    if not last_2:
        print("No chat history found for the given thread_id")
        return state
    prompt = PromptTemplate.from_template(
"""
You are a travel normalization system.

The user said: "{user_query}"
users last message is: {last_2}

Extract only the information directly mentioned by the user.

**Instructions:**
- Only extract **real locations** (countries, regions, cities) **IF** they are explicitly named.
- DO NOT extract words like "city," "town," "place," or "destination" as locations.
- DO NOT assume a location based on context.
- If no explicit location is mentioned, return an empty array.
-Extract price given by user in numbers.
- Extract months or seasons ONLY if they are explicitly mentioned, e.g. "July", "Winter", "Summer".
- Convert seasons to the corresponding months using this mapping:
- Map seasons to months using:
    - Summer → ["April", "May", "June"]
    - Monsoon → ["July", "August", "September"]
    - Autumn → ["October", "November"]
    - Winter → ["December", "January", "February"]
    - Spring → ["March", "April"]
- Do not extract months as the season.
-Identify user's priority if mentioned, such as "travel_time", "location", "activities", "property", or "postcard".
-User query will contain any of the above keywords. and use above words only as outputs.
-If user did not mention any priority then return empty array.
Output a valid JSON object only :

Example:
{{
  "possible_locations": [],
  "possible_activities": [],
  "possible_months": []
  "prices": []
  "resolved_priority": []
}}
DO NOT GIVE ANY EXPLANATION
"""
)

    rendered_prompt = prompt.format(
        user_query=state["user_query"],
        last_2=json.dumps(last_2, indent=2)
    )

    response = send_to_azure_openai(rendered_prompt)
    print(response)

    clean_json = re.sub(r"^```(?:json)?|```$", "", response.strip(), flags=re.IGNORECASE).strip()
    if not clean_json.strip().startswith("{"):
        clean_json = "{}"
    try:
        extracted = json.loads(clean_json)
    except json.JSONDecodeError:
        extracted = {
            "possible_locations": [],
            "possible_activities": [],
            "possible_months": [],
            "prices": [],
            "resolved_priority": None
        }

        # Extracted from LLM
    user_locations = extracted.get("possible_locations", [])
    user_activities = extracted.get("possible_activities", [])
    user_months = extracted.get("possible_months", [])
    user_prices = extracted.get("prices", [])
    resolved_priority = extracted.get("resolved_priority")
    if isinstance(resolved_priority, list) and resolved_priority:
        resolved_priority = resolved_priority[0]  # take first element if list
    elif not isinstance(resolved_priority, str):
        resolved_priority = None  # fallback

    

    # Semantic match
    matched_locations = semantic_match(" ".join(user_locations), location_labels, location_vectors)
    chunks = chunk_text(state['user_query'])

    matched_activities = []
    for chunk in chunks:
        matched = semantic_match(chunk, activity_labels, activity_vectors)
        matched_activities.extend(matched)

    # ✅ Set into state first
    state["months"] = user_months
    state["prices"] = user_prices
    state["matched_locations"] = matched_locations
    state["matched_activities"] = matched_activities
    if resolved_priority:
        state["resolved_priority"] = resolved_priority
    print(f"Matched locations: {matched_locations}")
    print(f"Matched activities: {matched_activities}")

    existing_prefs = get_preferences(thread_id) or {}

    # ⚠️ Merge only if new data is present
    location_to_save = matched_locations[0][0] if matched_locations else existing_prefs.get("location")

    existing_activities = set(existing_prefs.get("activities", [])) if existing_prefs else set()
    new_activities = set([a[0] for a in matched_activities])
    activities_to_save = list(existing_activities.union(new_activities))  # ✅ merge

    existing_months = set(existing_prefs.get("months", [])) if existing_prefs else set()
    months_to_save = list(existing_months.union(user_months)) if user_months else existing_prefs.get("months", [])

    existing_prices = set(existing_prefs.get("prices", [])) if existing_prefs else set()
    prices_to_save = list(existing_prices.union(user_prices)) if user_prices else existing_prefs.get("prices", [])

    # Only update if we actually have something new
    has_updates = any([
        location_to_save and (not existing_prefs or location_to_save != existing_prefs.get("location")),
        resolved_priority and resolved_priority != existing_prefs.get("resolved_priority"),

        set(activities_to_save) != set(existing_prefs.get("activities", [])) if existing_prefs else False,
        set(months_to_save) != set(existing_prefs.get("months", [])) if existing_prefs else False,
        set(prices_to_save) != set(existing_prefs.get("prices", [])) if existing_prefs else False
    ])

    if has_updates:
        print(f"🧠 Updating preferences in DB for thread_id: {thread_id}")
        save_preferences(
            thread_id=thread_id,
            location=location_to_save,
            activities=activities_to_save,
            months=months_to_save,
            prices=prices_to_save,
            resolved_priority=resolved_priority
        )



    # Save to state for immediate use
    state["matched_locations"] = matched_locations
    state["matched_activities"] = matched_activities
    state["months"] = user_months
    state["prices"] = user_prices

    return state

def extract_info(state: dict):
    thread_id = state.get("thread_id")
    prefs = get_preferences(thread_id) or {}
    matched_locations = state.get("matched_locations", [])
    matched_activities = state.get("matched_activities", [])
    possible_months = state.get("possible_months", [])

    state["location"] = [prefs.get("location")] if prefs.get("location") else []
    state["activities"] = prefs.get("activities", [])
    state["months"] = prefs.get("months", [])
    state["prices"] = prefs.get("prices", [])
    state["resolved_priority"] = prefs.get("resolved_priority")


    if matched_locations:
        # Take only the top matched location (highest score)
        top_location = matched_locations[0][0]
        matched_countries = [top_location]


        # Check if state["location"] exists and has at least one overlapping location
        existing_locations = state.get("location", [])

        if not all(loc in existing_locations for loc in matched_countries):
            state["location"] = matched_countries
        



    existing_activities = state.get("activities", [])
    for activity, _ in matched_activities:
        if activity not in existing_activities:
            existing_activities.append(activity)

    if existing_activities:
        state["activities"] = existing_activities
    
    existing_months = state.get("months", [])
    for month in possible_months:
        if month not in existing_months:
            existing_months.append(month)
    if existing_months:
        state["months"] = existing_months

    state["has_enough_info"] = bool(state.get("location") or state.get("activities") or state.get("months"))
    return state

def detect_conflicting_priorities(state: dict):
    months = state.get("months", [])
    prices = state.get("prices", [])
    chosen_priority = state.get("priority_field", "")
    user_query = state.get("user_query", "")

    if (months or prices) and chosen_priority:
        extras = []
        if months:
            extras.append("travel time")
        if prices:
            extras.append("budget")

        extras_str = " and ".join(extras)

        # Stronger prompt: nudges user to choose clearly
        priority_prompt = PromptTemplate.from_template(
            """
You're a helpful travel assistant.

The user said: "{user_query}"

You've detected that the user cares about multiple things — {extras_str} as well as {chosen_priority}.

💡 Ask the user politely but clearly:
For example, "I noticed you mentioned {extras_str} and {chosen_priority}. Which one is most important to you when choosing a destination?":
"Among these — {extras_str} and {chosen_priority} — which is most important to you when choosing a destination?"

Encourage them to pick one. This will help narrow the search. Keep the tone friendly but focused.

Only return the assistant’s message.
"""
        ).format(user_query=user_query, extras_str=extras_str, chosen_priority=chosen_priority)

        response = sllm.invoke([system_prompt, HumanMessage(content=priority_prompt)])
        print(response.content)
        # Clean up the response 
      


        return {
            **state,
            "search_results": [],
            "need_more_input": True,
            "followup": response.content.strip()
        }

    return state

# def extract_resolved_priority(state: dict):
#     user_reply = state.get("user_query", "")
    
#     print("🧠 Resolving user priority from reply:", user_reply)

#     # ---- Prompt to classify the reply ----
#     priority_extraction_prompt = PromptTemplate.from_template(
#         """
# You are a helpful assistant. The user previously mentioned multiple preferences and was asked which one they care about most.

# Now the user replied: "{user_reply}"

# Extract which one they want to prioritize the most:
# - Choose from one of these: "budget", "travel time", "location", "activity", "property", "postcard"
# - Return only a JSON string like this:
#   {{ "resolved_priority": "budget" }}
#         """
#     ).format(user_reply=user_reply)

#     response = sllm.invoke([
#         system_prompt,
#         HumanMessage(content=priority_extraction_prompt)
#     ])

#     print("🔍 Resolved priority raw response:", response.content)

#     try:
#         match = re.search(r'"resolved_priority"\s*:\s*"([^"]+)"', response.content)
#         resolved = match.group(1) if match else None
#     except Exception:
#         resolved = None

#     if resolved:
#         state["resolved_priority"] = resolved.strip().lower()
#         print("✅ User resolved priority:", resolved)
#     else:
#         print("⚠️ Could not extract resolved priority")

#     return state
