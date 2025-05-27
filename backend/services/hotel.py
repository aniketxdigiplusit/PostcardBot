from langchain.schema import HumanMessage
from qdrant_client import QdrantClient
from utils.helpers import system_prompt,send_to_openai,send_to_openai
from config.settings import llm, qdrant, COLLECTION_NAME, OLLAMA_API_URL
import numpy as np
import logging
import requests
from typing import List
from utils.helpers import client

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
        response = send_to_openai(prompt)  # Call LLM function
        hotel_name = response.strip()
        print(f"Extracted Hotel Name: {hotel_name}")  # Debugging line
        
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
    print("Embeddings created")

    search_results = qdrant.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_embedding,
        limit=200,
        with_payload=True,
        with_vectors=True  # Ensure extra_vectors are returned
    )

    if not search_results:
        return {**state, "chatbot_response": f"No hotels found for '{hotel_name}'."}
    
    print("200 search results")

    best_result = None
    best_score = 0

    for res in search_results:
        payload = res.payload
        vectors = res.vector if hasattr(res, "vector") else {}

        name_embed = res.vectors.get("name") if hasattr(res, "vectors") else payload.get("embedding_name", [])
        intro_embed = res.vectors.get("intro") if hasattr(res, "vectors") else payload.get("embedding_intro", [])

        name_sim = cosine_similarity(query_embedding, name_embed or []) * FIELD_WEIGHTS["name"]
        intro_sim = cosine_similarity(query_embedding, intro_embed or []) * FIELD_WEIGHTS["intro"]

        total_score = (name_sim + intro_sim) / sum(FIELD_WEIGHTS.values())

        if total_score > best_score:
            best_result = res
            best_score = total_score

    print("best result", best_result)

    if not best_result:
        return {**state, "chatbot_response": f"Sorry, I couldn't find a good match for '{hotel_name}'."}

    hotel_data = best_result.payload
    state["price_info"] = hotel_data.get("pricesStartingAt", "Price not available")
    state["hotel_name"] = hotel_name
    state["hotel_intro"] = hotel_data.get("intro", "")
    state["postcards"] = hotel_data.get("postcards", [])
    state["best_time_to_travel"] = hotel_data.get("bestTimetoTravel", "")

    hotel_real_name = hotel_data.get("name", "")
    postcards = hotel_data.get("postcards", [])
    best_time_to_travel = hotel_data.get("bestTimetoTravel", "")
    hotel_intro = hotel_data.get("intro", "")
    price = hotel_data.get("price", hotel_data.get("pricesStartingAt", ""))

    response_lines = [
        f"🏨 **{hotel_real_name}**",
        f"📍 {hotel_intro}",
        f"🕒 Best time to visit: {best_time_to_travel}",
        f"💰 Estimated Price: {price}",
        "",
        "✨ **Experiences & Postcards:**"
    ]

    if not postcards:
        response_lines.append("No postcards found for this hotel.")
    else:
        for idx, card in enumerate(postcards, start=1):
            name = card.get('name', 'Unnamed Experience')
            intro = card.get('intro', 'No description provided.')
            response_lines.append(f"{idx}. **{name}**: {intro}")

    response_text = "\n".join(response_lines)

    return {**state, "chatbot_response": response_text, "search_results": [hotel_data]}

def generate_embedding(text: str):
    """Generate embedding using OpenAI text-embedding-ada-002 model."""
 
    if not text.strip():
        print("generate_embedding() called with empty text.")
        return []
 
    try:
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=text.strip()
        )
 
        embedding = response.data[0].embedding
 
        if not embedding:
            print("Empty embedding generated for input text.")
            return []
 
        return embedding
 
    except Exception as e:
        print(f"Unexpected error in generate_embedding(): {e}")
        return []