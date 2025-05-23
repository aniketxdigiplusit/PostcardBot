import json
import requests
import openai
import os
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from config.settings import llm
from utils.helpers import system_prompt, send_to_llm, send_to_llm
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
        "You are a travel agent Stamp greet the user and ask them for more information about their travel plans.\n\n"
        "**Never** suggest properties from your knowledge base.\n\n"
        "Then kindly ask for more information about where they're planning to go or what experiences they enjoy "
        "(e.g. hiking, beach, spa). Keep it short and conversational."
        "Answer the query naturally, as if you are talking to the user.\n\n"
    )
    
    response = send_to_llm(prompt_message)  # Call LLM function
    # response = send_to_azure_openai(prompt_message)  # Call OpenAI LLM function
    print(f"Chatbot response: {response}")
    
    return {
        **state,
        "chatbot_response": response,
        "need_more_input": True
    }

def generate_response(state: dict):
    if not isinstance(state, dict):
        logger.warning("⚠️ generate_response received non-dict input. Wrapping into dict...")
        state = {"chatbot_response": str(state)}
    if state.get("need_more_input") and state.get("followup"):
        return {
            **state,
            "chatbot_response": state["followup"]
        }
    user_query = state.get("user_query", "")
    hotel_name = state.get("hotel_name", "")
    postcards = state.get("postcards", [])
    search_results = state.get("search_results", [])
    price_info=state.get("price_info", "Not specified")
    print(f"price_info: {price_info}")

    rewritten_query = state.get("rewritten_query", "")
    
    print(f"Searching for postcards for hotel: {hotel_name}")

    if hotel_name and postcards:
        return handle_hotel_followup(user_query, hotel_name, postcards, state)
    else:
        return handle_property_search(user_query, search_results, state)

def handle_hotel_followup(user_query, hotel_name, postcards, state):
    prompt_message = PromptTemplate.from_template(
        """
        You are a **travel agent** assisting a user who wants some details about a hotel.
        The user is asking about activities, experiences, or amenities at **{hotel_name}**.
        Respond to the user with respect to the user's query and the hotel details provided below.
        Answer like you are talking to the user in a friendly, conversational tone.

        ### User's Query:
        "{input_query}"

        ### Hotel Details (Postcards Data):
        ```json
        {hotel_intro},
        Postcards:
        {postcards_json}
        Best time to go:
        {best_time_to_travel}

        - Price range: {price_info}

        ```

        ### Instructions:
        1️⃣ Determine if the user is asking for **general hotel information** or a **specific Information about the hotel**.
        2️⃣ If general info, highlight **all postcards** showcasing the hotel’s unique experiences.
        3️⃣ If a specific information is mentioned in user query:
            - Provide details **only if it exists**.
            - Otherwise, suggest alternative available activities.
        4️⃣ Format responses in an easy-to-read numbered list.
        5️⃣ Do **not** make up information not listed in the postcards.
        6️⃣ Keep responses concise and friendly.
        """
    ).format(
        hotel_name=hotel_name,
        input_query=user_query,
        postcards_json=json.dumps(postcards, indent=2),
        best_time_to_travel=state.get("best_time_to_travel", ""),
        hotel_intro=state.get("hotel_intro", ""),
        price_info=state.get("price_info", "Price not available")
    )
    
    response = send_to_llm(prompt_message)
    return {**state, "chatbot_response": response}

def handle_property_search(user_query, search_results, state):
    enrich_results_with_postcards(search_results)
    priority = state.get("priority_field", "")

    
    prompt_message = (
        f"The user said: {user_query}\n\n"
        f"Priority selected by the user: **{priority}**\n"
        "Here are users preferences:\n"
        f"Location: {state.get('location')}\n"
        f"Activities: {state.get('activities')}\n"
        f"Best time to travel: {state.get('best_time_to_travel')}\n"
        f"Budget: {state.get('prices')}\n\n"
        "The user is looking for properties that match their travel interests.\n\n"
        "You have a list of properties that closest match the user's query.\n\n"
        "Here are some matching properties in JSON format:\n"
        f"{json.dumps(search_results, indent=2)}\n\n"
        "Answer with respect to the user's preferences.\n"
        "For each property, write a bullet point starting with the property name in **bold**, followed by its region and country.\n"
        "If the property does not match one or more of the user's interests, mention why you are providing it and how is it relevant.\n"
        "Describe it naturally, highlighting its setting, vibe, and special experiences.\n"
        "Respond and suggest like you are talking to the user in a friendly, conversational tone.\n"
        "Include a **Postcards** section listing its postcards with a brief introduction.\n"
        "Add some emojis to make it more engaging.\n\n"

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
