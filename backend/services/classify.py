from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from config.settings import llm
from utils.helpers import system_prompt, send_to_llm, send_to_azure_openai
from services.hotel import extract_hotel_name_from_query
import logging

logger = logging.getLogger(__name__)

def classify_input(state: dict):
    """
    Classifies the refined user query into:
    - greeting
    - hotel_followup

    - normal query
    """
    print("🚨 classify_input() is being called 🚨")


    user_query = state.get("user_query", "")

    # --- Classification Prompt ---
    classification_prompt = f"""
You are a travel chatbot assistant.

Your task is to classify the following user query into exactly one of these categories:

1. "greeting" — if the user is just saying hi, hello, thanks, okay, or other small talk.
2. "hotel_followup" — if the user is asking for more information about a specific hotel, mentions a hotel name, or wants details, activities, photos, or experiences related to a hotel.
3. "normal" — for all other queries related to destinations, activities, or general travel plans (excluding greetings and hotel followups).

### Example Classification:
- "Hi" → greeting
- "Tell me more about Taj Lake Palace" → hotel_followup
-"I want to travel in July" → normal
- "I want to plan a trip to Rajasthan for trekking" → normal

### Query:
{user_query}

Output only the classification value: greeting, hotel_followup, or normal.
Do not explain.
Do not output anything else.
"""
    response= send_to_llm(classification_prompt)  # Call LLM function
    classification = response.lower().strip()

    # response = llm.invoke([system_prompt, HumanMessage(content=classification_prompt)])
    # classification = response.content.strip().lower()

    # Enforce only allowed values
    if classification not in ["greeting", "hotel_followup", "normal"]:
        classification = "normal"
    print("classification result:", classification)
    state["query_type"] = classification

    # If it's a hotel followup, also extract the hotel name
    if classification == "hotel_followup":
        hotel_name = extract_hotel_name_from_query(user_query)
        if hotel_name and hotel_name.lower() != "none":
            state["hotel_name"] = hotel_name

    return state
