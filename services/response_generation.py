import json
import requests
import openai
import os
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from config.settings import llm
from utils.helpers import system_prompt, send_to_llm, send_to_azure_openai

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
    """
    Generates a chatbot response providing travel recommendations based on user query and search results.
    """
    def get_follow_up_instruction():
        has_location = bool(state.get("location"))
        has_activities = bool(state.get("activities"))

        if has_location and not has_activities:
            return "At the end, gently ask what kind of activities or experiences the user is most looking forward to."
        elif has_activities and not has_location:
            return "At the end, gently ask where the user is thinking of traveling to."
        return "You don't need to ask any follow-up question."

    def enrich_results_with_postcards(search_results):
        for result in search_results:
            album_id = result.get("id")
            if album_id:
                result["postcards"] = fetch_postcards(album_id)

    search_results = state.get("search_results", [])
    user_query = state.get("user_query", "")
    
    enrich_results_with_postcards(search_results)
    
    prompt_message = (
        f"The user said: {user_query}\n\n"
        "Here are some matching properties in JSON format:\n"
        f"{json.dumps(search_results, indent=2)}\n\n"
        "You're a warm, friendly travel advisor helping someone find a perfect getaway.\n\n"
        "For each property, write a bullet point starting with the property name in **bold**, followed by its region and country if available.\n"
        "Describe it in a natural, flowing paragraph — highlight its setting, vibe, and any special experiences or activities.\n"
        "Then, include a **Postcards** section listing its postcards, each in a bullet point, with the postcard's name in **bold** and a short introduction.\n"
        "Do not number the properties or call them 'Property 1', 'Property 2', etc.\n"
        "Keep the tone friendly and helpful, like you're chatting with someone planning their dream trip.\n\n"
        f"{get_follow_up_instruction()}"
    )

    response = send_to_llm(prompt_message)
    # response = send_to_azure_openai(prompt_message)
    
    return {
        **state,
        "chatbot_response": response
    }
