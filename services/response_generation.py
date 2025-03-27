import json
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from config.settings import llm
from utils.helpers import system_prompt

def get_more_info(state: dict):
    prompt = PromptTemplate.from_template(
        """The user said: \"{user_query}\"

Acknowledge their message in a warm, friendly tone. Then kindly ask for more information about where they're planning to go or what experiences they enjoy (e.g. hiking, beach, spa). Keep it short and conversational."""
    ).format(user_query=state["user_query"])

    response = llm.invoke([system_prompt, HumanMessage(content=prompt)])

    return {
        **state,
        "chatbot_response": response.content,
        "need_more_input": True
    }

def generate_response(state: dict):
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
        properties_json=json.dumps(state["search_results"], indent=2),
        follow_up_instruction=follow_up_instruction
    )

    response = llm.invoke([system_prompt, HumanMessage(content=prompt)])

    return {
        **state,
        "chatbot_response": response.content
    }
