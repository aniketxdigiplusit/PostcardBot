from langchain.schema import HumanMessage
from qdrant_client import QdrantClient
from utils.helpers import system_prompt
from config.settings import llm, qdrant, COLLECTION_NAME, OLLAMA_API_URL
import numpy as np
import logging
import requests
from typing import List

logger = logging.getLogger(__name__)


def extract_hotel_name_from_query(user_query: str) -> str:
    """
    Extracts the hotel name from the user's query using LLM.
    Returns the hotel name or empty string if not found.
    """

    prompt = f"""
You are an AI assistant. Extract the hotel name from the user's query.

- Only return the hotel name, nothing else.
- If no hotel name is found, return "None" (as a plain string).
- DO NOT explain.

Examples:
1. "Tell me more about Windermere Riverhouse" → "Windermere Riverhouse"
2. "What activities are available at Backwaters & Beyond?" → "Backwaters & Beyond"
3. "I want details about the first hotel you suggested." → "None"

User Query: {user_query}

Output only the hotel name or "None".
"""

    try:
        response = llm.invoke([system_prompt, HumanMessage(content=prompt)])
        hotel_name = response.content.strip()
        logger.info(f"✅ Extracted Hotel Name: {hotel_name}")
        return hotel_name if hotel_name.lower() != "none" else ""
    except Exception as e:
        logger.error(f"🔥 Error extracting hotel name: {e}")
        return ""

FIELD_WEIGHTS = {
    "name": 5.0,
    "intro": 3.0
}

def cosine_similarity(vec1, vec2):
    if not vec1 or not vec2:
        return 0.0
    vec1, vec2 = np.array(vec1), np.array(vec2)
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))

def hotel_followup(state: dict):
    user_query = state.get("user_query", "")
    hotel_name = extract_hotel_name_from_query(user_query)
    if not hotel_name:
        return {**state, "chatbot_response": "Sorry, I couldn't find which hotel you are referring to."}

    logger.info(f"🔍 Searching for hotels matching: {hotel_name}")

    query_embedding = generate_embedding(hotel_name)

    search_results = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_embedding,
        limit=200,
        with_payload=True
    )

    if not search_results:
        return {**state, "chatbot_response": f"No hotels found for '{hotel_name}'."}

    # -----------------------
    # Weighted Similarity Matching (only name & intro)
    # -----------------------
    best_result = None
    best_score = 0

    for res in search_results:
        payload = res.payload

        name_sim = cosine_similarity(query_embedding, generate_embedding(payload.get("name", ""))) * FIELD_WEIGHTS["name"]
        intro_sim = cosine_similarity(query_embedding, generate_embedding(payload.get("intro", ""))) * FIELD_WEIGHTS["intro"]

        total_score = (name_sim + intro_sim) / sum(FIELD_WEIGHTS.values())

        if total_score > best_score:
            best_result = res
            best_score = total_score
    print("best result", best_result)

    if not best_result:
        return {**state, "chatbot_response": f"Sorry, I couldn't find a good match for '{hotel_name}'."}

    hotel_data = best_result.payload
    hotel_real_name = hotel_data.get("name", "")
    postcards = hotel_data.get("postcards", [])

    # -----------------------
    # Response
    # -----------------------

    response_text = f"Here are some postcards from **{hotel_real_name}**:\n"
    if not postcards:
        response_text += "No postcards found for this hotel."
    else:
        for card in postcards:
            response_text += f"- **{card.get('name', '')}**: {card.get('intro', '')}\n"

    return {**state, "chatbot_response": response_text, "search_results": [hotel_data]}



def generate_embedding(text: str) -> List[float]:
    """Generate embedding using nomic-embed-text model with robust error handling."""
    
    if not text.strip():
        logger.warning("generate_embedding() called with empty text.")
        return []

    context = f"Travel query context: User Input: {text}"
    
    embedding_url = f"{OLLAMA_API_URL}/api/embeddings"
    payload = {"model": "nomic-embed-text", "prompt": context}

    try:
        response = requests.post(embedding_url, json=payload, timeout=30)
        response.raise_for_status()

        embedding = response.json().get("embedding", [])

        if not embedding:
            logger.warning("Empty embedding generated for input text.")
            return []

        return embedding

    except requests.exceptions.Timeout:
        logger.error("Embedding request timed out.")
        return []

    except requests.exceptions.RequestException as e:
        logger.error(f"Embedding API request error: {e}")
        return []

    except Exception as e:
        logger.error(f"Unexpected error in generate_embedding(): {e}")
        return []
