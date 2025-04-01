import json
import requests
import openai
import os
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from config.settings import llm
from utils.helpers import system_prompt
from services.chat_db import save_message
import logging

logger = logging.getLogger(__name__)


load_dotenv()

def fetch_postcards(album_id):
    params = {
        "filters[album][id][$eq]": album_id,  # Correct Strapi filter format
        "fields[0]": "id",
        "fields[1]": "name",
        "fields[2]": "intro",
        "fields[3]": "slug",
    }

    url = "https://development-api.postcard.travel/api/postcards"

    response = requests.get(url, params=params)

    try:
        data = response.json()
        print(data)
        if response.status_code == 200 and "data" in data:
            return data["data"]
    except Exception as e:
        print(f"Error parsing response: {e}")

    return []
def get_more_info(state: dict):
    prompt = PromptTemplate.from_template(
        """The user said: \"{user_query}\"

Acknowledge their message in a warm, friendly tone. Then kindly ask for more information about where they're planning to go or what experiences they enjoy (e.g. hiking, beach, spa). Keep it short and conversational."""
    ).format(user_query=state["user_query"])

    response = llm.invoke([system_prompt, HumanMessage(content=prompt)])
    bot_response = response.content.strip()



    return {
        **state,
        "chatbot_response": bot_response,
        "need_more_input": True
    }

def generate_response(state: dict):
    user_query = state.get("user_query", "")
    search_results = state.get("search_results", [])   
    hotel_name = state.get("hotel_name", "")
    logger.info(f"Searching for postcards for hotel: {hotel_name}")
    postcards = state.get("postcards", [])

    # ---------------------------------------------
    # Case 1: Hotel Followup detected
    # ---------------------------------------------
    if hotel_name and postcards:
        prompt = PromptTemplate.from_template(
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
        1️⃣ Look at the user’s query and determine if they are:
        - Asking for **general hotel information** (e.g., "Tell me more about Windermere Riverhouse")
        - Asking about a **specific activity** (e.g., "Does this hotel offer scuba diving?")

        2️⃣ If the user asks for general hotel info:
        - Display **all postcards** and highlight experiences that make the hotel unique.

        3️⃣ If the user asks about a specific activity (e.g., boating, trekking, spa):
        - First, check if this activity is mentioned in the postcards.
        - If the activity exists: Give details about that activity only from the corresponding postcard.
        - If the activity is NOT available: Clearly tell the user that the hotel does not offer this, but suggest **alternative available activities** from the postcards.

        4️⃣ Always format the response in an easy-to-read numbered list.
        5️⃣ Do not make up activities that are not in the postcards.
        6️⃣ Be concise and friendly in your response.
        """
        ).format(
            hotel_name=hotel_name,
            input_query=user_query,
            postcards_json=json.dumps(postcards, indent=2)
        )

    # ---------------------------------------------
    # Case 2: Normal property search flow
    # ---------------------------------------------
    else:
        has_location = bool(state.get("location"))
        has_activities = bool(state.get("activities"))

        if has_location and not has_activities:
            follow_up_instruction = (
                "At the end, gently ask what kind of activities or experiences the user is most looking forward to."
            )
        elif has_activities and not has_location:
            follow_up_instruction = (
                "At the end, gently ask where the user is thinking of traveling to."
            )
        else:
            follow_up_instruction = "You don't need to ask any follow-up question."

        search_results = state.get("search_results", [])
        for result in search_results:
            album_id = result["id"]
            result["postcards"] = fetch_postcards(album_id)

        prompt = PromptTemplate.from_template(
            "The user said: {user_query}\n\n"
            "Here are some matching properties in JSON format:\n"
            "{properties_json}\n\n"
            "You're a warm, friendly travel advisor helping someone find a perfect getaway.\n\n"
            "For each property, write a bullet point starting with the property name in **bold**, followed by its region and country if available.\n"
            "Describe it in a natural, flowing paragraph — highlight its setting, vibe, and any special experiences or activities.\n"
            "Do not number the properties or call them 'Property 1', 'Property 2', etc.\n"
            "Keep the tone friendly and helpful, like you're chatting with someone planning their dream trip.\n\n"
            "{follow_up_instruction}"
        ).format(
            user_query=state["user_query"],
            properties_json=json.dumps(state.get("search_results", []), indent=2),
            follow_up_instruction=follow_up_instruction
        )

    response = llm.invoke([system_prompt, HumanMessage(content=prompt)])
    bot_response = response.content.strip()

    return {
        **state,
        "chatbot_response": bot_response
    }
# import openai

# openai_client = openai.AzureOpenAI(
#     api_key=os.getenv("AZURE_OPENAI_API_KEY"),
#     api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
#     azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT")
# )

# def call_gpt(messages):
#     # Ensure content is a string
#     for msg in messages:
#         if not isinstance(msg["content"], str):
#             msg["content"] = str(msg["content"])  # Convert objects to string

#     response = openai_client.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=messages
#     )
#     return response.choices[0].message.content



# def get_more_info(state: dict):
#     prompt = PromptTemplate.from_template(
#         """The user said: \"{user_query}\" 

# Acknowledge their message in a warm, friendly tone. Then kindly ask for more information about where they're planning to go or what experiences they enjoy (e.g. hiking, beach, spa). Keep it short and conversational."""
#     ).format(user_query=state["user_query"])

#     response = call_gpt([
#         {"role": "system", "content": system_prompt},
#         {"role": "user", "content": prompt}
#     ])

#     return {
#         **state,
#         "chatbot_response": response,
#         "need_more_input": True
#     }

# def generate_response(state: dict):
#     has_location = bool(state.get("location"))
#     has_activities = bool(state.get("activities"))

#     follow_up_instruction = (
#         "At the end, gently ask what kind of activities or experiences the user is most looking forward to."
#         if has_location and not has_activities else
#         "At the end, gently ask where the user is thinking of traveling to."
#         if has_activities and not has_location else
#         "You don't need to ask any follow-up question."
#     )

#     prompt = PromptTemplate.from_template(
#         "The user said: {user_query}\n\n"
#         "Here are some matching properties in JSON format:\n"
#         "{properties_json}\n\n"
#         "You're a warm, friendly travel advisor helping someone find a perfect getaway.\n\n"
#         "For each property, write a bullet point starting with the property name in **bold**, followed by its region and country if available.\n"
#         "Describe it in a natural, flowing paragraph — highlight its setting, vibe, and any special experiences or activities.\n"
#         "Do not number the properties or call them 'Property 1', 'Property 2', etc.\n"
#         "Keep the tone friendly and helpful, like you're chatting with someone planning their dream trip.\n\n"
#         "{follow_up_instruction}"
#     ).format(
#         user_query=state["user_query"],
#         properties_json=json.dumps(state["search_results"], indent=2),
#         follow_up_instruction=follow_up_instruction
#     )

#     response = call_gpt([
#         {"role": "system", "content": system_prompt},
#         {"role": "user", "content": prompt}
#     ])

#     return {
#         **state,
#         "chatbot_response": response
#     }
