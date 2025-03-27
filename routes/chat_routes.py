import uuid
from flask import Blueprint, request, jsonify
from services.chat_service import create_chat_graph
from models import db, ChatSession

chat_blueprint = Blueprint("chat", __name__)

@chat_blueprint.route("/", methods=["POST"])
def start_chat():
    chat_id = str(uuid.uuid4())
    data = request.json
    query = data.get("query", "")

    # Create and run chat graph
    graph = create_chat_graph()
    state = {"user_query": query, "chat_id": chat_id}
    response = graph.invoke(state)

    # Store session in database
    session = ChatSession(id=chat_id, state=response)
    db.session.add(session)
    db.session.commit()

    return jsonify({
        "chat_id": chat_id,
        "response": response["chatbot_response"]
    })

@chat_blueprint.route("/<chat_id>", methods=["POST"])
def continue_chat(chat_id):
    session = ChatSession.query.get(chat_id)
    if not session:
        return jsonify({"error": "Invalid chat session"}), 404

    state = session.state

    # Get new user query
    data = request.json
    query = data.get("query", "")
    state["user_query"] = query

    # Process and update state
    graph = create_chat_graph()
    response = graph.invoke(state)

    # Update session in database
    session.state = response
    db.session.commit()

    return jsonify({"chat_id": chat_id, "response": response["chatbot_response"]})
