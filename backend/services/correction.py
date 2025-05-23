from config.db import get_preferences, save_preferences
import json
from utils.helpers import send_to_llm

def correction_node(state: dict):
    user_query = state.get("user_query", "")
    thread_id = state.get("thread_id")

    print(f"📝 Correction Node triggered. User said: {user_query}")

    # 🔹 LLM Prompt to extract corrections safely
    correction_prompt = f"""
You are a travel assistant managing user's preferences.

User just said: "{user_query}"

Do the following:
- Only update fields explicitly mentioned by the user.
- Do NOT change location, activities, months, or prices unless the user clearly refers to them.
- If user says "forget March", only update months.
- If user says "no not Nepal", update location.
- If nothing to change, leave empty.

Respond in this JSON format:
{{
  "reset_all": false,
  "updated_fields": {{
    "location": [],
    "activities": [],
    "months": [],
    "prices": []
  }}
}}
"""
    response = send_to_llm(correction_prompt)
    print(f"🔍 Correction LLM Response: {response}")

    try:
        correction_data = json.loads(response)
    except json.JSONDecodeError:
        print("❌ Invalid correction response. Skipping update.")
        return {**state, "chatbot_response": "Sorry, I couldn't process that. Can you clarify what you'd like to update?"}

    prefs = get_preferences(thread_id) or {}
    updates = correction_data.get("updated_fields", {})

    # ✅ Handle "Forget Everything" Reset
    if correction_data.get("reset_all"):
        print("🗑️ User requested full reset of preferences.")
        save_preferences(
            thread_id=thread_id,
            location=[],
            activities=[],
            months=[],
            prices=[],
            resolved_priority=None
        )
        return {**state, "chatbot_response": "Got it! All your preferences have been reset."}

    # ✅ Validate Changes (diff check)
    validated_updates = {}
    for field in ["location", "activities", "months", "prices"]:
        new_values = updates.get(field, [])
        if new_values and prefs.get(field) != new_values:
            validated_updates[field] = new_values

    if validated_updates:
        print(f"✅ Applying validated updates: {validated_updates}")
        save_preferences(
            thread_id=thread_id,
            **validated_updates
        )
        return {**state, "chatbot_response": "Updated your preferences as per your request!"}
    else:
        print("❌ No actual changes detected. Skipping save.")
        return {**state, "chatbot_response": "It seems like your preferences are already up to date!"}


