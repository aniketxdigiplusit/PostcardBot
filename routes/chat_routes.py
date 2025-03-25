import uuid
from flask import Blueprint, request, jsonify
from services.chat_service import create_chat_graph

chat_blueprint = Blueprint('chat', __name__)

# Session storage
chat_sessions = {}

@chat_blueprint.route('/', methods=['POST'])
def start_chat():
    chat_id = str(uuid.uuid4())
    data = request.json
    query = data.get('query', '')

    # Create and run chat graph
    graph = create_chat_graph()
    state = {"user_query": query, "chat_id": chat_id}
    response = graph.invoke(state)

    # Store session state
    chat_sessions[chat_id] = {"graph": graph, "state": response}

    return jsonify({
        "chat_id": chat_id,
        "response": response["chatbot_response"]
    })

@chat_blueprint.route('/<chat_id>', methods=['POST'])
def continue_chat(chat_id):
    if chat_id not in chat_sessions:
        return jsonify({"error": "Invalid chat session"}), 404

    session = chat_sessions[chat_id]
    graph = session['graph']
    state = session['state']

    # Get new user query
    data = request.json
    query = data.get('query', '')
    state["user_query"] = query

    # Process and update state
    response = graph.invoke(state)
    chat_sessions[chat_id] = {"graph": graph, "state": response}

    return jsonify({"chat_id": chat_id, "response": response["chatbot_response"]})
