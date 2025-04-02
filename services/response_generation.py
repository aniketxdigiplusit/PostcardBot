import json
import requests
import openai
import os
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from config.settings import llm
from utils.helpers import system_prompt, send_to_llm
from services.chat_db import save_message
import logging

logger = logging.getLogger(__name__)


load_dotenv()

def fetch_postcards(album_id):
    params = {
        "filters[album][id][$eq]": album_id,  # Correct Strapi filter format
        "filters[isComplete][$eq]": True,  # Correct Strapi filter format
        "fields[0]": "id",
        "fields[1]": "name",
        "fields[2]": "intro",
        "fields[3]": "slug",
    }

    url = "https://development-api.postcard.travel/api/postcards"

    response = requests.get(url, params=params)

    try:
        data = response.json()
        # print(data)
        if response.status_code == 200 and "data" in data:
            return data["data"]
    except Exception as e:
        print(f"Error parsing response: {e}")

    return []

def get_more_info(state: dict):
    """
    Generates a chatbot response asking the user for more information about their travel plans or experiences.
    """
    prompt_message = (
        f"The user said: \"{state['user_query']}\"\n\n"
        "Acknowledge their message in a warm, friendly tone. "
        "**Never** suggest properties from your knowledge base.\n\n"
        "Then kindly ask for more information about where they're planning to go or what experiences they enjoy "
        "(e.g. hiking, beach, spa). Keep it short and conversational."
    )
    
    response = send_to_llm(prompt_message)  # Call LLM function
    # response = send_to_azure_openai(prompt_message)  # Call OpenAI LLM function
    
    return {
        **state,
        "chatbot_response": response,
        "need_more_input": True
    }

def generate_response(state: dict):
    user_query = state.get("user_query", "")
    hotel_name = state.get("hotel_name", "")
    postcards = state.get("postcards", [])
    search_results = state.get("search_results", [])
    
    logger.info(f"Searching for postcards for hotel: {hotel_name}")

    if hotel_name and postcards:
        return handle_hotel_followup(user_query, hotel_name, postcards, state)
    else:
        return handle_property_search(user_query, search_results, state)

def handle_hotel_followup(user_query, hotel_name, postcards, state):
    prompt_message = PromptTemplate.from_template(
        """
        You are a **travel agent** assisting a user who wants more details about a hotel.
        The user is asking about activities, experiences, or amenities at **{hotel_name}**.

        ### User's Query:
        "{input_query}"

        ### Hotel Details (Postcards Data):
        ```json
        {postcards_json}
        ```

        ### Instructions:
        1️⃣ Determine if the user is asking for **general hotel information** or a **specific activity**.
        2️⃣ If general info, highlight **all postcards** showcasing the hotel’s unique experiences.
        3️⃣ If a specific activity is mentioned:
            - Provide details **only if it exists** in the postcards.
            - Otherwise, suggest alternative available activities.
        4️⃣ Format responses in an easy-to-read numbered list.
        5️⃣ Do **not** make up activities not listed in the postcards.
        6️⃣ Keep responses concise and friendly.
        """
    ).format(
        hotel_name=hotel_name,
        input_query=user_query,
        postcards_json=json.dumps(postcards, indent=2)
    )
    
    response = send_to_llm(prompt_message)
    return {**state, "chatbot_response": response}

def handle_property_search(user_query, search_results, state):
    enrich_results_with_postcards(search_results)
    
    prompt_message = (
        f"The user said: {user_query}\n\n"
        "Here are some matching properties in JSON format:\n"
        f"{json.dumps(search_results, indent=2)}\n\n"
        "You're a warm, friendly travel advisor helping someone find a perfect getaway.\n\n"
        "For each property, write a bullet point starting with the property name in **bold**, followed by its region and country.\n"
        "Describe it naturally, highlighting its setting, vibe, and special experiences.\n"
        "Include a **Postcards** section listing its postcards with a brief introduction.\n"
        "Do not number the properties. Keep the tone friendly and engaging.\n\n"
        f"{get_follow_up_instruction(state)}"
    )
    
    response = send_to_llm(prompt_message)
    return {**state, "chatbot_response": response}

def enrich_results_with_postcards(search_results):
    for result in search_results:
        if album_id := result.get("id"):
            result["postcards"] = fetch_postcards(album_id)

def get_follow_up_instruction(state):
    has_location = bool(state.get("location"))
    has_activities = bool(state.get("activities"))
    
    if has_location and not has_activities:
        return "At the end, gently ask what kind of activities the user is most looking forward to."
    elif has_activities and not has_location:
        return "At the end, gently ask where the user is thinking of traveling to."
    return "You don't need to ask any follow-up question."
