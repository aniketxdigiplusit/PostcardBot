from services.chat_db import get_chat_messages
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from config.settings import llm
from utils.helpers import system_prompt, send_to_llm, send_to_azure_openai
import logging

logger = logging.getLogger(__name__)

def get_context(state: dict):
    user_input = state.get("user_query", "").strip()
    thread_id = state.get("chat_id")

    if not thread_id:
        logger.warning("Missing thread_id in state")
        return state

    messages = get_chat_messages(thread_id, limit=6)
    last_6 = messages[:6] if len(messages) > 6 else messages
     # Debugging line
    if not last_6:
        logger.warning("No chat history found for the given thread_id")
        return state

    formatted_history = "\n".join(f"{msg['sender'].capitalize()}: {msg['text']}" for msg in last_6)
    print(f"Formatted History: {formatted_history}")  

    llm_prompt = f"""
You are an AI assistant for a travel chatbot. Your task is to only refine user queries **ONLY** when they are incomplete or ambiguous and rely on previous chat history. Do not try to reply to the query.

**Chat History:** 
{formatted_history}

**New User Query:** 
{user_input}

Instructions:
- Keep greetings or small talk unchanged.
- Do not insert or assume locations, activities, budgets, or preferences unless mentioned clearly.
- If the query is already clear (e.g., "I want to go to Rajasthan"), repeat it exactly.
-If the query is asking for a specific hotel, replace it with the exact name from chat history.
    Example: "Tell me more about the first hotel you suggested" → "Tell me more about Windermere Riverhouse"
   Example: "Tell me more about the first hotel you suggested" → "Tell me more about Windermere Riverhouse"
-If the query is asking answering to a preference from previous context, rewrite the previous query with the preference.
    Example: " I prefer budget more"- " I want to go nepal in 200 budget and my preference is budget"

### Output Format:
Return only the refined query text, without comments, explanations, or formatting. 
If you don't need to modify the query, repeat it exactly as it is.

"""
    response= send_to_azure_openai(llm_prompt)

    # response = send_to_azure_openai([system_prompt, HumanMessage(content=llm_prompt)])
    print(f"LLM Response: {response.strip()}")  # Debugging line

    enriched_query = response.strip() or user_input

    state["user_query"] = enriched_query
    return state
