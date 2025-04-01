from services.chat_db import get_chat_messages
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from config.settings import llm
from utils.helpers import system_prompt
import logging

logger = logging.getLogger(__name__)

def get_context(state: dict):
    user_input = state.get("user_query", "")
    thread_id = state.get("chat_id")

    if not thread_id:
        logger.warning("Missing thread_id in state")
        return state

    messages = get_chat_messages(thread_id, limit=15)
    last_15 = messages[-15:] if len(messages) > 15 else messages

    formatted_history = ""
    for msg in last_15:
        formatted_history += f"{msg['sender'].capitalize()}: {msg['text']}\n"
    
    print(formatted_history)
    

    # Step 4: Prompt Preparation
    llm_prompt = f"""
You are an AI assistant for a travel chatbot. Your task is to refine user queries ONLY when they are incomplete or ambiguous and rely on previous chat history.

**Chat History:** 
{formatted_history}

**New User Query:** 
{user_input}

### STRICT RULES:
- DO NOT add any locations, activities, budgets, preferences, or examples that were originally suggested by the bot unless the user explicitly confirms or mentions them again.
- DO NOT assume, invent, or guess user interests or preferences.
- DO NOT enrich the query based on your general knowledge or common sense.
- ONLY rewrite if the user is referring back to something from the previous chat like "the first one", "those hotels", "that location", etc.
- If the query is standalone (e.g., "I want to go to Rajasthan"), just repeat it exactly as it is.

### Instructions:
1. If the query is a follow-up depending on previous context, rewrite it to be clear and standalone.
2. If the query is standalone, return it unchanged.
3. DO NOT inject into the query any content that was only part of the bot's suggestions unless the user explicitly mentioned it.
4.If the query is asking for a hotel or property from previous context then rewrite it with the hotel name.
Example: "Tell me more about the first hotel you suggested" → "Tell me more about Windermere Riverhouse"

### Output Format:
Just reply with the query text only.
No explanations.
No comments.
No markdown.
No formatting.

If you don't need to modify the query, repeat it exactly as it is.
"""

    response = llm.invoke([system_prompt, HumanMessage(content=llm_prompt)])
    print(response.content)

    enriched_query = response.content.strip() or user_input

    state["user_query"] = enriched_query
    return state