import uuid
from flask import Blueprint, request, jsonify
from services.chat_service import create_chat_graph
from services.chat_db import save_message
from flask import Blueprint, jsonify
from models import db, ChatHistory
from qdrant_client import QdrantClient
from flask import request


chat_blueprint = Blueprint("chat", __name__)
# Initialize Qdrant client
qdrant = QdrantClient(host="localhost", port=6333)
def get_site_stats_from_qdrant():
    all_points = []
    offset = None

    while True:
        points, next_page_offset = qdrant.scroll(
            collection_name="postcard-openai",
            scroll_filter=None,
            with_payload=True,
            limit=100,
            offset=offset
        )
        all_points.extend(points)

        if next_page_offset is None:
            break
        offset = next_page_offset

    locations = set()
    properties = 0
    activities = set()
    postcard_count = 0

    for point in all_points:
        payload = point.payload

        if payload.get("name"):
            properties += 1

        if payload.get("region"):
            locations.add(payload["region"])
        elif payload.get("country"):
            locations.add(payload["country"])

        for act in payload.get("activities", []):
            activities.add(act.lower())

        # Count postcards if available
        postcards = payload.get("postcards", [])
        if isinstance(postcards, list):
            postcard_count += len(postcards)

    return {
        "locations": len(locations),
        "properties": properties,
        "activities": len(activities),
        "postcards": postcard_count
    }

get_site_stats_from_qdrant()
def generate_welcome_message():
    stats = get_site_stats_from_qdrant()
    return (
       "🌍 Hi, I'm Stach – your guide at the Postcard Travel Club, a community for conscious luxury travellers.\n\n"
        f"We currently feature:\n"
        f"• {stats['locations']} breathtaking **locations** 📍\n"
        f"• {stats['properties']} soulful **properties** 🏨\n"
        f"• {stats['activities']} unforgettable **experiences** 🌿\n"
        f"• {stats['postcards']} unique **postcards** 📸\n\n"
        "A *wonder-full* world is waiting for you. Where shall we begin?"
    )

@chat_blueprint.route("/startup-messages/<input>", methods=["GET"])
def get_startup_messages(input):
    stats = get_site_stats_from_qdrant()

    welcome_message = (
        "🌍 Hi, I'm Stamp – your guide at the Postcard Travel Club, a community for conscious luxury travellers.\n\n"
        f"We currently feature:\n"
        f"• {stats['locations']} breathtaking **locations** 📍\n"
        f"• {stats['properties']} soulful **properties** 🏨\n"
        f"• {stats['activities']} unforgettable **experiences** 🌿\n"
        f"• {stats['postcards']} unique **postcards** 📸\n\n"
        "A *wonder-full* world is waiting for you. Where shall we begin?"
    )

    priority_messages = {
        "properties": f"I'm so glad you're exploring our properties! 🏨 We currently have {stats['properties']} soulful boutique properties. Which type of stay are you drawn to?",
        "location": f"Thinking about locations? 🌍 We feature {stats['locations']} breathtaking destinations. Where do you see yourself traveling next?",
        "postcards": f"You’re going to love this! 💌 We’ve captured over {stats['postcards']} inspiring postcards to fuel your wanderlust. Ready to explore?",
        "activities": f"We offer {stats['activities']} unforgettable experiences 🌿 – from cultural immersions to adventure getaways. What excites you most?"
    }

    if input in priority_messages:
        return jsonify({"response": priority_messages[input]})
    elif input == "welcome":
        return jsonify({"response": welcome_message})


@chat_blueprint.route("/", methods=["POST"])
def start_chat():
    chat_id = str(uuid.uuid4())
   
    data = request.json
    original_query = data.get("query", "")
    priority_field = data.get("priority_field", "")  #  get priority from frontend

    graph = create_chat_graph()
    state = {
        "user_query": original_query,
        "thread_id": chat_id,
        "priority_field": priority_field  # pass it to the state
    }
    response = graph.invoke(state) #Runs the bot logic and gets a reply.

    save_message(
        thread_id=chat_id,
        user_message=original_query,
        bot_response=response.get("chatbot_response", "")
    )

    return jsonify({
        "thread_id": chat_id,
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
        "thread_id": chat_id,
        "priority_field": priority_field  # ✅ pass it to the state
    }

    graph = create_chat_graph()
    response = graph.invoke(state)
    # ⚡ Wrap response if it's not dict
    if not isinstance(response, dict):
        print("⚠️ Response was not a dict. Wrapping...")
        response = {"chatbot_response": str(response)}


    save_message(
        thread_id=chat_id,
        user_message=original_query,
        bot_response=response.get("chatbot_response", "")
    )

    return jsonify({
        "thread_id": chat_id,
        "response": response.get("chatbot_response", ""),
        "search_results": response.get("search_results", [])
    })


chat_api = Blueprint("chat_api", __name__)

# 🔹 Get all unique thread IDs
@chat_api.route("/api/threads", methods=["GET"])
def get_all_threads():
    threads = db.session.query(ChatHistory.thread_id).distinct().all()
    return jsonify([t[0] for t in threads])

# 🔹 Get all chats for a given thread_id
@chat_api.route("/api/chats/<thread_id>", methods=["GET"])
def get_chats_by_thread(thread_id):
    chats = ChatHistory.query.filter_by(thread_id=thread_id).order_by(ChatHistory.timestamp).all()
    formatted_chats = []

    for chat in chats:
        formatted_chats.append({"sender": "user", "text": chat.user_message})
        formatted_chats.append({"sender": "bot", "text": chat.bot_response})

    return jsonify(formatted_chats)
