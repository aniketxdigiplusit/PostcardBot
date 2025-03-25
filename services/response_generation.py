import json
from langchain.prompts import PromptTemplate
from langchain.schema import HumanMessage
from config.settings import llm

def get_more_info(state: dict):
    prompt = f"The user said: \"{state['user_query']}\"\n\nAsk for more details in a friendly tone."
    response = llm.invoke([HumanMessage(content=prompt)])
    return {**state, "chatbot_response": response.content, "need_more_input": True}

def generate_response(state: dict):
    prompt = PromptTemplate.from_template(
        "The user said: {user_query}\n\n"
        "Matching properties in JSON:\n"
        "{properties_json}\n\n"
        "Write a warm, friendly response."
    ).format(
        user_query=state["user_query"],
        properties_json=json.dumps(state["search_results"], indent=2),
    )

    response = llm.invoke([HumanMessage(content=prompt)])
    return {**state, "chatbot_response": response.content}
