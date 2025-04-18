import uuid
from flask import Blueprint, request, jsonify
from services.chat_service import create_chat_graph
from services.chat_db import save_message
from models import db,ChatHistory

chat_blueprint = Blueprint("chat", __name__)

@chat_blueprint.route("/", methods=["POST"])
def start_chat():
    chat_id = str(uuid.uuid4())
    greeting_message = (
        "👋 Welcome to **Postcard Travel** – a conscious luxury travel platform!\n\n"
        "✨ We offer:\n"
        "• Over 150+ boutique **properties** 🏨\n"
        "• 300+ unique **postcards** from around the world 📸\n"
        "• Rich **experiences** across 25+ countries 🌍\n\n"
        "🎒 Whether you're looking for glamping in Rajasthan or cultural retreats in Japan – we're here to help you explore mindfully.\n"
        "Start by telling me where you want to go or what you'd like to experience!"
    )

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
        "thread_id": chat_id,
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


@chat_blueprint.route("/threads", methods=["GET"])
def get_all_threads():
    try:
        threads = db.session.query(ChatHistory.thread_id).distinct().all()
        unique_thread_ids = [t[0] for t in threads]
        return jsonify({"thread_ids": unique_thread_ids})
    except Exception as e:
        print(f"Error retrieving thread IDs: {e}")
        return jsonify({"error": "Failed to retrieve thread IDs"}), 500
    
@chat_blueprint.route("/threads/<thread_id>", methods=["GET"])
def get_thread_messages(thread_id):
    try:
        messages = ChatHistory.query.filter_by(thread_id=thread_id) \
                                    .order_by(ChatHistory.timestamp.desc()) \
                                    .all()

        message_list = [
            {
                "id": msg.id,
                "user_message": msg.user_message,
                "bot_response": msg.bot_response,
                "timestamp": msg.timestamp.isoformat()
            }
            for msg in messages
        ]

        return jsonify({"thread_id": thread_id, "messages": message_list})
    except Exception as e:
        print(f"Error retrieving messages for thread {thread_id}: {e}")
        return jsonify({"error": "Failed to retrieve messages"}), 500
