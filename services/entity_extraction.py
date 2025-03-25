import json
import re
from langchain.schema import SystemMessage, HumanMessage
from langchain.prompts import PromptTemplate
from config.settings import sllm
from models.embeddings import semantic_match, location_labels, location_vectors, activity_labels, activity_vectors

def normalize_entities(state: dict):
    prompt = PromptTemplate.from_template(
"""
You are a travel normalization system.

The user said: "{user_query}"

Your job is to extract only travel-related information that the user explicitly and directly mentioned. Do NOT guess, assume, or infer anything.

🚨 STRICT RULES:
- Only extract **real locations** (countries, regions, cities) **IF** they are explicitly named.
- ❌ DO NOT extract words like "city," "town," "place," or "destination" as locations.
- ❌ DO NOT assume a location based on context.
- If no explicit location is mentioned, return an empty array.

Output a valid JSON object only:

Example:
{{
  "possible_locations": [],
  "possible_activities": []
}}
"""
)

    rendered_prompt = prompt.format(user_query=state["user_query"])
    response = sllm.invoke([system_prompt, HumanMessage(content=rendered_prompt)])

    clean_json = re.sub(r"^```(?:json)?|```$", "", response.content.strip(), flags=re.IGNORECASE).strip()
    if not clean_json.strip().startswith("{"):
        clean_json = "{}"

    try:
        extracted = json.loads(clean_json)
    except json.JSONDecodeError:
        extracted = {"possible_locations": [], "possible_activities": []}

    user_locations = extracted.get("possible_locations", [])
    user_activities = extracted.get("possible_activities", [])

    matched_locations = semantic_match(" ".join(user_locations), location_labels, location_vectors)
    matched_activities = semantic_match(" ".join(user_activities), activity_labels, activity_vectors)

    state["matched_locations"] = matched_locations
    state["matched_activities"] = matched_activities

    # Save top location for quick access
    state["normalized_locations"] = matched_locations[0][0] if matched_locations else ""
    state["normalized_activities"] = [act[0] for act in matched_activities]

    return state

def extract_info(state: dict):
    matched_locations = state.get("matched_locations", [])
    matched_activities = state.get("matched_activities", [])

    if "location" not in state and matched_locations:
        state["location"] = matched_locations[0][0]

    existing_activities = state.get("activities", [])
    for activity, _ in matched_activities:
        if activity not in existing_activities:
            existing_activities.append(activity)

    if existing_activities:
        state["activities"] = existing_activities

    state["has_enough_info"] = bool(state.get("location") or state.get("activities"))
    return state
