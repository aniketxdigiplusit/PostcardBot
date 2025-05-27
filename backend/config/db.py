# db.py
import sqlite3
from flask import Flask, jsonify
import json
import os


DB_FILE = "chat_preferences.db"
DB_PATH=os.path.join(os.path.dirname(__file__), DB_FILE)
app = Flask(__name__)


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Ensure the table exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
    thread_id TEXT PRIMARY KEY,
    location TEXT,
    activities TEXT,
    months TEXT,
    prices TEXT,
    resolved_priority TEXT,
    asked_resolve_priority BOOLEAN DEFAULT FALSE
)
    """)
    conn.commit()
    conn.close()

init_db()

def save_preferences(thread_id, location=None, activities=None, months=None, prices=None, resolved_priority=None, asked_resolve_priority=False):
    print(f"🧠 Saving preferences to DB for thread_id: {thread_id}")
    print("location:", location)
    print("activities:", activities)
    print("months:", months)
    print("prices:", prices)
    print("resolved_priority:", resolved_priority)
    print("asked_resolve_priority:", asked_resolve_priority)

    activities_json = json.dumps(activities or [])
    months_json = json.dumps(months or [])
    prices_json = json.dumps(prices or [])
    resolved_priority_json = json.dumps(resolved_priority or None)

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT thread_id FROM preferences WHERE thread_id = ?", (thread_id,))
        exists = cursor.fetchone()

        if exists:
            cursor.execute("""
                UPDATE preferences
                SET location = ?, activities = ?, months = ?, prices = ?, resolved_priority = ?, asked_resolve_priority = ?
                WHERE thread_id = ?
            """, (location, activities_json, months_json, prices_json, resolved_priority_json, asked_resolve_priority, thread_id))
        else:
            cursor.execute("""
                INSERT INTO preferences (thread_id, location, activities, months, prices, resolved_priority, asked_resolve_priority)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (thread_id, location, activities_json, months_json, prices_json, resolved_priority_json, asked_resolve_priority))

        print("✅ Preferences saved successfully")
        conn.commit()



def get_preferences(thread_id):
    print(f"🧠 Retrieving preferences from DB for thread_id: {thread_id}")
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT location, activities, months, prices, resolved_priority, asked_resolve_priority FROM preferences WHERE thread_id = ?", (thread_id,))
        row = cursor.fetchone()

        if row:
            return {
                "location": row[0],
                "activities": json.loads(row[1] or "[]"),
                "months": json.loads(row[2] or "[]"),
                "prices": json.loads(row[3] or "[]"),
                "resolved_priority": None if row[4] == "null" else row[4],
                "asked_resolve_priority": bool(row[5]) 
            }
        return None




# CHAT_DB_PATH = os.path.join(os.path.dirname(__file__), "chat.db")

# # @app.route("/api/threads", methods=["GET"])
# # def get_all_thread_ids():
# #     with sqlite3.connect(CHAT_DB_PATH) as conn:
# #         cursor = conn.cursor()
# #         cursor.execute("SELECT DISTINCT thread_id FROM chats")
# #         threads = [row[0] for row in cursor.fetchall()]
# #     return jsonify(threads)

# # @app.route("/api/chats/<thread_id>", methods=["GET"])
# # def get_chats_by_thread(thread_id):
# #     try:
# #         with sqlite3.connect(CHAT_DB_PATH) as conn:
# #             cursor = conn.cursor()
# #             cursor.execute("""
# #                 SELECT sender, text, timestamp
# #                 FROM messages
# #                 WHERE thread_id = ?
# #                 ORDER BY timestamp ASC
# #             """, (thread_id,))
# #             rows = cursor.fetchall()

# #         messages = [
# #             {
# #                 "sender": row[0],
# #                 "text": row[1],
# #                 "timestamp": row[2]
# #             }
# #             for row in rows
# #         ]

# #         return jsonify({
# #             "thread_id": thread_id,
# #             "messages": messages
# #         })

# #     except Exception as e:
# #         print("Error fetching messages:", e)
# #         return jsonify({"error": "Internal server error"}), 500
    
# # if __name__ == "__main__":
# #     app.run(debug=True)