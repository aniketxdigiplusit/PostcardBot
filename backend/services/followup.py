# followup_utils.py

from langchain.schema import HumanMessage
from config.settings import sllm  # Your LLM client
import logging
from utils.helpers import system_prompt, send_to_llm

logger = logging.getLogger(__name__)

def generate_followups_from_response(chatbot_response: str, history=[], user_query: str = "") -> list:
    """
    Generate contextual follow-up questions based on chatbot's latest response and conversation history.
    """

    history_text = "\n".join([f"{msg['sender']}: {msg['text']}" for msg in history[-8:]])

    prompt = f"""
You're a helpful travel assistant for conscious luxury travel.

The user just asked:
"{user_query}"

You replied:
"{chatbot_response}"

Recent conversation:
{history_text}

Based on this, suggest 4 to 5 **short, helpful follow-up messages** the user might say next to keep the discovery going.

Rules:
- Keep each suggestion under 12 words.
- Be relevant to the current assistant message.
- Avoid vague or repetitive questions.
- Focus on travel properties, experiences, postcards, destinations, best time to go, or budgets.

Examples:
• Tell me more about Windermere hotel
• What’s the best time to visit Bhutan?
• Show me experiences in Rishikesh
• Are there romantic getaways in that region?
• Explore similar postcards

Return follow-up suggestions as a plain bullet list. Nothing else.
"""

    try:
        result = send_to_llm(prompt)  # This may return a string or Langchain LLM object
        # Handle both cases
        if hasattr(result, "content"):
            output_text = result.content
        else:
            output_text = result

        print("Generated follow-ups:", output_text)
        lines = output_text.strip().split("\n")
        followups = [line.lstrip("•-0123456789. ").strip() for line in lines if line.strip()]
        return followups[:5]

    except Exception as e:
        logger.warning(f"⚠️ Failed to generate followups: {e}")
        return []
