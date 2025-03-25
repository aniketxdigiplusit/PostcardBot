from langgraph.graph import StateGraph, END
from services.entity_extraction import normalize_entities, extract_info
from services.property_search import retrieve_properties
from services.response_generation import generate_response, get_more_info

def process_query(state: dict):
    message = state["user_query"].lower()
    state.setdefault("chat_history", []).append(message)
    return {**state}

def create_chat_graph():
    graph = StateGraph(dict)
    
    graph.add_node("process_query", process_query)
    graph.add_node("normalize_entities", normalize_entities)
    graph.add_node("extract_info", extract_info)
    graph.add_node("get_more_info", get_more_info)
    graph.add_node("retrieve_properties", retrieve_properties)
    graph.add_node("generate_response", generate_response)

    graph.set_entry_point("process_query")

    graph.add_edge("process_query", "normalize_entities")
    graph.add_edge("normalize_entities", "extract_info")

    graph.add_conditional_edges(
        "extract_info",
        lambda s: "retrieve_properties" if s.get("has_enough_info") else "get_more_info"
    )

    graph.add_edge("get_more_info", END)
    graph.add_edge("retrieve_properties", "generate_response")
    graph.add_edge("generate_response", END)

    return graph.compile()
