import json
import re
from typing import List, Dict, Any
from services.chat_db import get_chat_messages
from langchain.schema import SystemMessage, HumanMessage
from langchain.prompts import PromptTemplate
from config.settings import sllm
from embeddings import semantic_match, location_labels, location_vectors, activity_labels, activity_vectors
from utils.helpers import system_prompt, send_to_openai, send_to_azure_openai, send_to_openai
from services.hotel import generate_embedding
from config.db import  get_preferences, save_preferences

def chunk_text(text, chunk_size=2, overlap=1):
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

# def determine_crud_operation(new_data, old_data, user_query=""):
#     # Convert sets to lists so json.dumps doesn't break
#     def safe_json(data):
#         return json.dumps(json.loads(json.dumps(data, default=list)), indent=2)

#     crud_prompt = f"""
# You are a system that determines how to update a user's travel preferences based on the **latest user query** and **existing preferences**.

# Analyze whether the user's query indicates:
# - replacing their old preferences (e.g., they want to explore a new destination or they dont want a previous destination or activity anymore),
# - merging (e.g., they want to add an activity or time preference to the existing location),
# - or ignore if nothing new is added.

# User Query: "{user_query}"

# Old Preferences: {safe_json(old_data)}

# New Input from Query: {safe_json(new_data)}

# Respond with ONLY ONE WORD: "merge", "replace", or "ignore".
# Example:
# - If the user says "I want to go to Paris and I also want to go to London", the system should respond with "merge".
# - If the user says "I want to go to Paris instead of London", the system should respond with "replace".
# -If the user says" I dont want to do boating anymore i want to do trekking", the system should respond with "replace".
# """

#     response = send_to_openai(crud_prompt)
#     print("🧠 CRUD decision:", response)
#     decision = response.strip().lower()
#     if decision not in ["merge", "replace", "ignore"]:
#         return "merge"
#     return decision

def normalize_entities(state: dict):
    thread_id = state.get("thread_id")
    print(f"Thread ID: {thread_id}")

    messages = get_chat_messages(thread_id, limit=6)
    last_2 = messages[:2] if len(messages) > 6 else messages
     

    prompt = PromptTemplate.from_template(
"""
You are a travel normalization system.

The user said: "{user_query}"
users last message is: {last_2}

Extract only the information directly mentioned by the user.

**Instructions:**
- Only extract **real locations** (countries, regions, cities) **IF** they are explicitly named.
- Do not extract words like "city," "town," "place," or "destination" as locations.
- Do not assume a location based on context.
- If no explicit location is mentioned, return an empty array.
-Extract price given by user in numbers.
- Extract months or seasons ONLY if they are explicitly mentioned, e.g. "July", "Winter", "Summer".
- Convert seasons to the corresponding months using this mapping:
- Do not extract months as the season.
-Do not extract words like location , place, city as possible location.
-Extract direct words in query like location, activities , time to travel, prices as resolved priority
-Extract is one word location or activity in user query.

Output a valid JSON object only :

Example:
{{
  "possible_locations": [],
  "possible_activities": [],
  "possible_months": [],
  "prices": [],
  "resolved_priority": []

  
}}
DO NOT GIVE ANY EXPLANATION
"""
    )

    rendered_prompt = prompt.format(
        user_query=state["user_query"],
        last_2=json.dumps(last_2, indent=2)
    )

    response = send_to_openai(rendered_prompt)
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
            # "resolved_priority": []
        }

    user_locations = extracted.get("possible_locations", [])
    user_activities = extracted.get("possible_activities", [])
    user_months = extracted.get("possible_months", [])
    user_prices = extracted.get("prices", [])
    # resolved_priority = extracted.get("resolved_priority")

    # if isinstance(resolved_priority, list) and resolved_priority:
    #     resolved_priority = resolved_priority[0].strip().lower()
    # elif isinstance(resolved_priority, str):
    #     resolved_priority = resolved_priority.strip().lower()
    # else:
    #     resolved_priority = None

    matched_locations = semantic_match(" ".join(user_locations), location_labels, location_vectors)
    chunks = chunk_text(state['user_query'])

    matched_activities = []
    for chunk in chunks:
        matched = semantic_match(chunk, activity_labels, activity_vectors)
        matched_activities.extend(matched)

    state["matched_locations"] = matched_locations
    state["matched_activities"] = matched_activities
    state["months"] = user_months
    state["prices"] = user_prices
    # if resolved_priority in ["location", "activities", "months", "prices"]:
    #     state["resolved_priority"] = resolved_priority

    print(f"Matched locations: {matched_locations}")
    print(f"Matched activities: {matched_activities}")

    existing_prefs = get_preferences(thread_id) or {}

    new_location = matched_locations[0][0] if matched_locations else None
    if new_location and new_location.lower() not in ["location", "place", "city"]:
        location_to_save = new_location
    else:
        location_to_save = existing_prefs.get("location")

    existing_activities = list(existing_prefs.get("activities", []))
    new_activities = [a[0] for a in matched_activities]

    # Remove duplicates and preserve order
    for activity in new_activities:
        if activity in existing_activities:
            existing_activities.remove(activity)  # Move to end
        existing_activities.append(activity)

    activities_to_save = existing_activities


    existing_months = set(existing_prefs.get("months", []))
    months_to_save = list(existing_months.union(user_months)) if user_months else existing_prefs.get("months", [])

    existing_prices = set(existing_prefs.get("prices", []))
    prices_to_save = list(existing_prices.union(user_prices)) if user_prices else existing_prefs.get("prices", [])

    # resolved_priority_to_save = resolved_priority if resolved_priority in ["location", "activities", "months", "prices"] else existing_prefs.get("resolved_priority")
    # # if resolved_priority_to_save=={} :
    # #             resolved_priority_to_save==None
    # print(f"Resolved priority to save: {resolved_priority_to_save}")

    has_updates = any([
        location_to_save and location_to_save != existing_prefs.get("location"),
        # resolved_priority_to_save and resolved_priority_to_save != existing_prefs.get("resolved_priority"),
        set(activities_to_save) != set(existing_prefs.get("activities", [])),
        set(months_to_save) != set(existing_prefs.get("months", [])),
        set(prices_to_save) != set(existing_prefs.get("prices", []))
    ])
    resolved_priority=existing_prefs.get("resolved_priority")
    asked_resolve_priority = existing_prefs.get("asked_resolve_priority", False)

    if has_updates:
        print(f"🧠 Updating preferences in DB for thread_id: {thread_id}")
        save_preferences(
            thread_id=thread_id,
            location=location_to_save,
            activities=activities_to_save,
            months=months_to_save,
            prices=prices_to_save,
            resolved_priority=resolved_priority,
            asked_resolve_priority=asked_resolve_priority

        )

    priority_field = state.get("priority_field")
    print(f"Priority field: {priority_field}")
    has_some_prefs = any([user_locations, user_activities, user_months, user_prices])

    if not priority_field and has_some_prefs:
        state["discovery_mode"] = True
        print("🌱 Discovery mode ON: priority not set, but some preferences exist.")
    else:
        state["discovery_mode"] = False
        print("❌ Discovery mode OFF: either priority was explicitly set or no prefs found.")

    
    
    prefs = get_preferences(state.get("thread_id")) or {}

    state["missing_fields"] = [
        k for k in ["location", "activities", "months", "prices"]
        if not prefs.get(k)
    ]
    state["asked_resolve_priority"] = prefs.get("asked_resolve_priority", False)


    return state



def extract_info(state: dict):
    print("🧠 extract_info() called.")
    print(f"➡️  discovery_mode: {state.get('discovery_mode')}")
    print(f"➡️  resolved_priority: {state.get('resolved_priority')}")
    print(f"➡️  missing_fields: {state.get('missing_fields')}")
    print(f"➡️  need_more_input: {state.get('need_more_input')}")
    print(f"➡️  priority_field: {state.get('priority_field')}")


    thread_id = state.get("thread_id")
    prefs = get_preferences(thread_id) or {}

    #  # ✅ Pull latest resolved_priority from DB
    # if not state.get("resolved_priority"):
    #     state["resolved_priority"] = prefs.get("resolved_priority")

    # Also ensure discovery_mode is still valid
    if not state.get("priority_field") and (prefs.get("location") or prefs.get("activities") or prefs.get("months")):
        state["discovery_mode"] = True
    matched_locations = state.get("matched_locations", [])
    matched_activities = state.get("matched_activities", [])
    possible_months = state.get("possible_months", [])

    state["location"] = [prefs.get("location")] if prefs.get("location") else []
    state["activities"] = prefs.get("activities", [])
    state["months"] = prefs.get("months", [])
    state["prices"] = prefs.get("prices", [])
    state["resolved_priority"] = prefs.get("resolved_priority")

    print(f"Matched locations: {state["location"]}")
    print(f"Matched activities: {state["activities"]}")
    print(f"Matched months: {state["months"]}")
    print(f"Matched prices: {state["prices"]}")


    if matched_locations:
        # Take only the top matched location (highest score)
        top_location = matched_locations[0]
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
        state["activities"] = existing_activities[-4:]
    
    existing_months = state.get("months", [])
    for month in possible_months:
        if month not in existing_months:
            existing_months.append(month)
    if existing_months:
        state["months"] = existing_months

    state["has_enough_info"] = bool(state.get("location") or state.get("activities") or state.get("months"))

        # ✅ Check if discovery_mode should be activated
    if not state.get("priority_field") and (state["location"] or state["activities"] or state["months"]):
        state["discovery_mode"] = True
    else:
        state["discovery_mode"] = False

    state["has_enough_info"] = bool(state["location"] or state["activities"] or state["months"])
    
    
    print("asked_resolve_priority", state["asked_resolve_priority"])
    print(state["activities"])
 

    print("Debugging",state.get("resolved_priority"), state.get("discovery_mode"))
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


def conversational_priority_prompt(user_input):
    prompt = f"""
You are a friendly travel assistant at Postcard Travel Club.

The user said: "{user_input}"

Your goal is to help the user decide what to explore first by responding conversationally.

Available options are:
- Properties
- Locations
- Experiences
- Postcards

Ask a friendly follow-up question that nudges the user to pick one of these, but DO NOT list them like a menu. Be natural, informal, and keep the tone helpful.

Return only your conversational reply.
"""
    response = send_to_openai(prompt)
    return response.strip()

def detect_missing_priority(state: dict):
    user_query = state.get("user_query", "")
    chosen_priority = state.get("priority_field", "")

    if not chosen_priority:
        from services.chat_service import conversational_priority_prompt
        prompt_response = conversational_priority_prompt(user_query)

        return {
            **state,
            "chatbot_response": prompt_response,
            "need_more_input": True,
            "search_results": []
        }

    return state
