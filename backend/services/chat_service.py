from langgraph.graph import StateGraph, END
from services.entity_extraction import normalize_entities, extract_info, detect_conflicting_priorities
from services.property_search import retrieve_properties
from services.response_generation import generate_response, get_more_info
from services.context import get_context
from services.classify import classify_input
from services.hotel import hotel_followup
from config.db import get_preferences

def process_query(state: dict):
    message = state["user_query"].lower()
    # state.setdefault("chat_history", []).append(message)
    return {**state}

def create_chat_graph():
    graph = StateGraph(dict)
    
    # ---------------- Nodes ----------------
    graph.add_node("process_query", process_query)
    graph.add_node("get_context", get_context)
    graph.add_node("normalize_entities", normalize_entities)
    graph.add_node("classify_input", classify_input)
    graph.add_node("extract_info", extract_info)
    graph.add_node("get_more_info", get_more_info)
    graph.add_node("retrieve_properties", retrieve_properties)
    graph.add_node("hotel_followup", hotel_followup)
    graph.add_node("detect_conflicting_priorities", detect_conflicting_priorities)
    graph.add_node("generate_response", generate_response)

    # ---------------- Entry ----------------
    graph.set_entry_point("process_query")

    # ---------------- Normalization pipeline ----------------
    graph.add_edge("process_query", "get_context")
    graph.add_edge("get_context", "normalize_entities")
    graph.add_edge("normalize_entities", "classify_input")

    # ---------------- Classify step ----------------
  # CLASSIFY input: normal path
    graph.add_conditional_edges(
        "classify_input",
        lambda s: "get_more_info" if s.get("query_type") == "greeting" else
                "hotel_followup" if s.get("query_type") == "hotel_followup" else
                "extract_info"
    )

    # EXTRACT INFO: do we need to ask for more or resolve conflicting preferences?
    graph.add_conditional_edges(
        "extract_info",
        lambda s: "get_more_info"
        if not s.get("location") and not s.get("activities")  
        else "detect_conflicting_priorities"
        if (s.get("months") or s.get("prices")) and not get_preferences(s.get("thread_id", "")).get("resolved_priority")  # 🧠 Ask user what to prioritize
        else "retrieve_properties"  # ✅ We're good
    )

    # After conflicting priority is resolved → either go back to extract or retrieve
    graph.add_conditional_edges(
    "detect_conflicting_priorities",
    lambda s: "generate_response" if s.get("need_more_input") else "retrieve_properties"
)
    # ---------------- All terminal nodes lead to generate_response ----------------
    graph.add_edge("hotel_followup", "generate_response")
    graph.add_edge("retrieve_properties", "generate_response")

    # ---------------- End ----------------
    
    graph.add_edge("get_more_info", END)
    graph.add_edge("generate_response", END)

    return graph.compile()
