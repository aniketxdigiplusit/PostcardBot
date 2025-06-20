import uuid
from flask import Blueprint, request, jsonify, g
from services.chat_service import create_chat_graph
from services.chat_db import save_message
from flask import Blueprint, jsonify
from models import db, ChatHistory
from qdrant_client import QdrantClient
from flask import request
from config.settings import qdrant
from embeddings import location_labels, activity_labels, property_labels
import random
from decode import jwt_required, check_rate_limit


chat_blueprint = Blueprint("chat", __name__)

chat_api = Blueprint("chat_api", __name__)
# Initialize Qdrant client

@chat_api.route("/secure", methods=["GET"])
@jwt_required
def secure_route():
    return jsonify({"message": "This is a secure endpoint", "user": g.user})



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

    if input == "location":
        random_locations = random.sample(location_labels, min(len(location_labels), 18))
        top_locations = random_locations[:4]
        remaining_locations = random_locations[4:]
        return jsonify({
            "response": priority_messages["location"],
            "top_locations": top_locations,
            "more_locations": remaining_locations
        })
    elif input == "activities":
        random_activities = random.sample(activity_labels, min(len(activity_labels), 12))
        return jsonify({
            "response": priority_messages["activities"],
            "top_activities": random_activities[:4],
            "more_activities": random_activities[4:]
        })

    elif input == "properties":
        random_properties = random.sample(property_labels, min(len(property_labels), 12))
        return jsonify({
            "response": priority_messages["properties"],
            "top_properties": random_properties[:4],
            "more_properties": random_properties[4:]
        })

    if input in priority_messages:
        return jsonify({"response": priority_messages[input]})

    # ✅ Default fallback (welcome)
    if input == "welcome":
        return jsonify({"response": welcome_message})

    return jsonify({"response": "Sorry, I didn't understand your selection."})

@chat_blueprint.route("/message", methods=["POST"])
@jwt_required
def handle_chat_message():
    data = request.get_json()
    user_message = data.get("message")

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # Access user info from JWT
    user = g.user  # Example: {'id': 1, 'email': 'user@example.com'}

    # Simulate a chatbot response
    bot_response = f"Hello {user.get('username', 'User')}, you said: {user_message}"

    return jsonify({
        "user": user,
        "bot_response": bot_response
    })

@chat_blueprint.route("/", methods=["POST"])
@jwt_required
def start_chat():
    chat_id = str(uuid.uuid4())
    data = request.json

    user = g.user

    original_query = data.get("query", "")
    priority_field = data.get("priority_field", "")
    ai_message = data.get("ai_response", "")  # this is the markdown AI content

    # ✅ If ai_response is present, save as know more chat without invoking the graph
    if ai_message:
        save_message(
            thread_id=chat_id,
            user_message="Know More",
            bot_response=ai_message
        )
        return jsonify({
            "thread_id": chat_id,
            "user": user,
            "response": None,
            "followups": []
        })

    # ✅ Otherwise, proceed with normal graph execution
    if not check_rate_limit(user.get("id")):
        return jsonify({"error": "Rate limit exceeded. Try again in 24 hours."}), 429

    graph = create_chat_graph()
    state = {
        "user_query": original_query,
        "thread_id": chat_id,
        "priority_field": priority_field,
        "user_id": user.get("id")
    }

    response = graph.invoke(state)

    save_message(
        thread_id=chat_id,
        user_message=original_query,
        bot_response=response.get("chatbot_response", "")
    )

    return jsonify({
        "thread_id": chat_id,
        "user": user,
        "response": response.get("chatbot_response", ""),
        "followups": response.get("followups", [])
    })




@chat_blueprint.route("/<chat_id>", methods=["POST"])
@jwt_required
def continue_chat(chat_id):
    data = request.json
    original_query = data.get("query", "")
    priority_field = data.get("priority_field", "")  # get priority from frontend
    result = data.get("result", {})

    user = g.user  # Access user info from JWT

    # Check if the user has exceeded the rate limit for follow-up
    if not check_rate_limit(user.get("id")):
        return jsonify({"error": "Rate limit exceeded. Try again in 24 hours."}), 429

    state = {
        "user_query": original_query,
        "thread_id": chat_id,
        "priority_field": priority_field,
        "followups": result.get("followups", []),
        # "user_id": user.get("id")
    }

    graph = create_chat_graph()
    response = graph.invoke(state)
    # Wrap response if it's not a dict
    if not isinstance(response, dict):
        response = {"chatbot_response": str(response)}

    save_message(
        thread_id=chat_id,
        user_message=original_query,
        bot_response=response.get("chatbot_response", "")
    )

    return jsonify({
        "thread_id": chat_id,
        "response": response.get("chatbot_response", ""),
        "search_results": response.get("search_results", []),
        "followups": response.get("followups", []),
        "user": user 
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
