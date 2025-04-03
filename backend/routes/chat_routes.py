import uuid
from flask import Blueprint, request, jsonify
from services.chat_service import create_chat_graph
from services.chat_db import save_message

chat_blueprint = Blueprint("chat", __name__)

@chat_blueprint.route("/", methods=["POST"])
def start_chat():
    chat_id = str(uuid.uuid4())
    data = request.json
    original_query = data.get("query", "")
    priority_field = data.get("priority_field", "")  # ✅ get priority from frontend

    graph = create_chat_graph()
    state = {
        "user_query": original_query,
        "chat_id": chat_id,
        "priority_field": priority_field  # ✅ pass it to the state
    }
    response = graph.invoke(state)

    save_message(
        thread_id=chat_id,
        user_message=original_query,
        bot_response=response.get("chatbot_response", "")
    )

    return jsonify({
        "chat_id": chat_id,
        "response": response.get("chatbot_response", "")
    })


@chat_blueprint.route("/<chat_id>", methods=["POST"])
def continue_chat(chat_id):
    data = request.json
    original_query = data.get("query", "")
    priority_field = data.get("priority_field", "")  # ✅ get priority from frontend
    print("Priority Field Received:", priority_field)


    state = {
        "user_query": original_query,
        "chat_id": chat_id,
        "priority_field": priority_field  # ✅ pass it to the state
    }

    graph = create_chat_graph()
    response = graph.invoke(state)

    save_message(
        thread_id=chat_id,
        user_message=original_query,
        bot_response=response.get("chatbot_response", "")
    )

    return jsonify({
        "chat_id": chat_id,
        "response": response.get("chatbot_response", ""),
        "search_results": response.get("search_results", [])
    })
