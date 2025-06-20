from langgraph.graph import StateGraph, END
from services.entity_extraction import normalize_entities, extract_info, detect_conflicting_priorities
from services.property_search import retrieve_properties
from services.response_generation import generate_response, get_more_info
from services.context import get_context
from services.classify import classify_input
from services.hotel import hotel_followup
from config.db import get_preferences
from services.postcard import explain_postcard_travel, explain_about_postcard
from services.discovery import start_discovery_flow, continue_discovery_flow, resolve_discovery_priority, extract_resolved_priority, retrieve_discovery_properties

# def process_query(state: dict):
#     message = state["user_query"].lower()
#     # state.setdefault("chat_history", []).append(message)
#     return {**state}
def create_chat_graph():
    graph = StateGraph(dict)

    # ---------------- Nodes ----------------
    graph.add_node("get_context", get_context)
    graph.add_node("normalize_entities", normalize_entities)
    graph.add_node("classify_input", classify_input)
    graph.add_node("extract_info", extract_info)
    graph.add_node("get_more_info", get_more_info)
    graph.add_node("retrieve_properties", retrieve_properties)
    graph.add_node("hotel_followup", hotel_followup)
    graph.add_node("detect_conflicting_priorities", detect_conflicting_priorities)
    graph.add_node("generate_response", generate_response)
    graph.add_node("explain_about_postcard", explain_about_postcard)
    graph.add_node("start_discovery_flow", start_discovery_flow)
    graph.add_node("continue_discovery_flow", continue_discovery_flow)
    graph.add_node("resolve_discovery_priority", resolve_discovery_priority)
    graph.add_node("extract_resolved_priority", extract_resolved_priority)
    graph.add_node("retrieve_discovery_properties", retrieve_discovery_properties)

    # ---------------- Entry ----------------
    graph.set_entry_point("get_context")

    # ---------------- Classification pipeline ----------------
    graph.add_edge("get_context", "classify_input")

    graph.add_conditional_edges(
        "classify_input",
        lambda s: "get_more_info" if s.get("query_type") == "greeting" else
                  "hotel_followup" if s.get("query_type") == "hotel_followup" else
                  "explain_about_postcard" if s.get("query_type") == "about" else
                  "normalize_entities"
    )
 

    graph.add_edge("normalize_entities", "extract_info")

    # ---------------- Extraction and Routing ----------------
    graph.add_conditional_edges(
    "extract_info",
    lambda s:  "continue_discovery_flow"
    if s.get("discovery_mode") and s.get("missing_fields")

    else "resolve_discovery_priority"
    if s.get("discovery_mode") and s.get("resolved_priority") == None and s.get("asked_resolve_priority") is False

    else "extract_resolved_priority"
    if s.get("discovery_mode") and not s.get("resolved_priority") and s.get("asked_resolve_priority") is True

    else "detect_conflicting_priorities"
    if s.get("discovery_mode") and (s.get("months") or s.get("prices")) and not get_preferences(s.get("thread_id", "")).get("resolved_priority")

    else "retrieve_properties"
    if s.get("discovery_mode") == False
    else "retrieve_discovery_properties"
    
    )

  
    graph.add_conditional_edges(
        "detect_conflicting_priorities",
        lambda s: "generate_response" if s.get("need_more_input") else "retrieve_properties"
    )

    # ---------------- End Paths ----------------
    graph.add_edge("get_more_info", END)
    graph.add_edge("generate_response", END)
    graph.add_edge("hotel_followup", "generate_response")
    graph.add_edge("retrieve_properties", "generate_response")
    graph.add_edge("explain_about_postcard", END)
    graph.add_edge("retrieve_discovery_properties", "generate_response")

    # 🔚 Discovery flow ends
    graph.add_edge("start_discovery_flow", END)
    graph.add_edge("continue_discovery_flow", END)
    graph.add_edge("resolve_discovery_priority", END )
    graph.add_edge("extract_resolved_priority", "retrieve_discovery_properties")

    return graph.compile()



def _log_and_return(target: str, state: dict = None):
    import logging
    logging.info(f"Routing to node: {target} with state keys: {list(state.keys()) if state else 'no state'}")
    return target