import json
import requests
import openai
import os
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from config.settings import llm
from utils.helpers import system_prompt, send_to_openai, send_to_azure_openai
from services.chat_db import save_message
import logging
from services.followup import generate_followups_from_response


logger = logging.getLogger(__name__)


load_dotenv()



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
    
    response = send_to_openai(prompt_message)  # Call LLM function
    followups = generate_followups_from_response(response, [], state.get("user_query", ""))
    print(f"followups: {followups}")  # Debugging line
    # response = send_to_azure_openai(prompt_message)  # Call OpenAI LLM function
    print(f"Chatbot response: {response}")
    
    return {
        **state,
        "chatbot_response": response,
        "followups": followups,
        "need_more_input": True
    }
def shorten_query(query, max_tokens=3000):
    # Split the query into words and check if it exceeds the limit
    tokens = query.split()
    if len(tokens) > max_tokens:
        query = " ".join(tokens[:max_tokens])
    return query

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
    print (f"Rewritten Query: {rewritten_query}")

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
    
    response = send_to_openai(prompt_message)
    followups = generate_followups_from_response(response, [], user_query)
    return {**state, "chatbot_response": response, "followups": followups,}

def handle_property_search(user_query, search_results, state):
    
    priority = state.get("priority_field", "")

    
    prompt_message = (
        f"User's Query: {user_query}\n\n"
    f"Based on what the user is asking, here is the relevant information to help with the response:\n"
    f"**User Preferences (only relevant if needed):**\n"
    f"Location: {state.get('location', 'Not specified')}\n"
    f"Activities: {state.get('activities', 'Not specified')}\n"
    f"Best time to travel: {state.get('best_time_to_travel', 'Not specified')}\n"
    f"Budget: {state.get('prices', 'Not specified')}\n\n"
    
    "Your task is to respond directly to the user's query. Use the following property details to answer their question:\n"
    "Here are some properties that closely match the user's query (in JSON format):\n"
    f"{json.dumps(search_results, indent=2)}\n\n"
    
    "Answer directly based on the user's query. If necessary, briefly mention preferences that are relevant, but focus on the user's query.\n"
    "For each property, include the following details:\n"
    "- Start with the property name in **bold**.\n"
    "- Mention the **region** and **country**.\n"
    "- Describe the **setting, vibe**, and **special experiences** that match the user's interests.\n"
    "- If the property does not fully align with the user's preferences, explain how it's still relevant and why it's being included.\n"
    "- Include a **Postcards** section to highlight the experiences available at the property, along with a brief introduction.\n"
    "- Use emojis to make the response more engaging and friendly.\n\n"

    "Your goal is to provide a concise, conversational response that helps the user make an informed decision."

       
    )
    
    prompt_message = shorten_query(prompt_message)

    try:
        response = send_to_openai(prompt_message)
        if not response:
            raise ValueError("Received empty response from OpenAI.")

        followups = generate_followups_from_response(response, [], user_query)
        return {**state, "chatbot_response": response, "followups": followups}
    except openai.error.RateLimitError:
        print("⚠️ Rate limit exceeded! Please try again later.")
        return {**state, "chatbot_response": "Sorry, I'm currently unable to process your request due to a high volume of traffic. Please try again later."}
    except Exception as e:
        print(f"⚠️ Error generating response: {e}")
        return {**state, "chatbot_response": "An error occurred. Please try again."}

# def enrich_results_with_postcards(search_results):
#     for result in search_results:
#         if album_id := result.get("id"):
#             result["postcards"] = fetch_postcards(album_id)
        

def get_follow_up_instruction(state):
    has_location = bool(state.get("location"))
    has_activities = bool(state.get("activities"))
    
    if has_location and not has_activities:
        return "At the end, gently ask what kind of activities the user is most looking forward to."
    elif has_activities and not has_location:
        return "At the end, gently ask where the user is thinking of traveling to."
    return "You don't need to ask any follow-up question."
