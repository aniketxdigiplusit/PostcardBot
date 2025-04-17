# db.py
import sqlite3
import json
import os
DB_FILE = "chat_preferences.db"
DB_PATH=os.path.join(os.path.dirname(__file__), DB_FILE)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            thread_id TEXT PRIMARY KEY,
            location TEXT,
            activities TEXT,
            months TEXT,
            prices TEXT,
            resolved_priority TEXT  )   
    
    """)
    conn.commit()
    conn.close()



def save_preferences(thread_id, location=None, activities=None, months=None, prices=None, resolved_priority=None):
    # Convert lists to JSON strings
    print(f"🧠 Saving preferences to DB for thread_id: {thread_id}")
    print("location:", location)
    print("activities:", activities)
    print("months:", months)
    print("prices:", prices)
    print("resolved_priority:", resolved_priority)
    activities_json = json.dumps(activities or [])
    months_json = json.dumps(months or [])
    prices_json = json.dumps(prices or [])

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Check if entry exists
        cursor.execute("SELECT thread_id FROM preferences WHERE thread_id = ?", (thread_id,))
        exists = cursor.fetchone()

        if exists:
            # Update existing
            cursor.execute("""
                UPDATE preferences
                SET location = ?, activities = ?, months = ?, prices = ?, resolved_priority = ?
                WHERE thread_id = ?
            """, (location, activities_json, months_json, prices_json, resolved_priority, thread_id))
        else:
            # Insert new
            cursor.execute("""
                INSERT INTO preferences (thread_id, location, activities, months, prices, resolved_priority)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (thread_id, location, activities_json, months_json, prices_json, resolved_priority))
        print("Preferences saved successfully!")
        print(resolved_priority)

        conn.commit()

def get_preferences(thread_id):
    print(f"🧠 Retrieving preferences from DB for thread_id: {thread_id}")
    
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT location, activities, months, prices, resolved_priority FROM preferences WHERE thread_id = ?", (thread_id,))
        row = cursor.fetchone()

        if row:
            return {
                "location": row[0],
                "activities": json.loads(row[1] or "[]"),
                "months": json.loads(row[2] or "[]"),
                "prices": json.loads(row[3] or "[]"),
                "resolved_priority": row[4]
            }
        return None

def update_preferences(thread_id, location=None, activities=None, months=None, prices=None):
    existing = get_preferences(thread_id)
    updated = {
        "location": location or existing.get("location"),
        "activities": activities or existing.get("activities"),
        "months": months or existing.get("months"),
        "prices": prices or existing.get("prices"),
    }
    save_preferences(
        thread_id,
        updated["location"],
        updated["activities"],
        updated["months"],
        updated["prices"]
    )

def delete_preferences(thread_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM preferences WHERE thread_id = ?", (thread_id,))
    conn.commit()
    conn.close()
def get_all_preferences():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM preferences")
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "thread_id": row[0],
            "location": row[1],
            "activities": json.loads(row[2] or "[]"),
            "months": json.loads(row[3] or "[]"),
            "prices": json.loads(row[4] or "[]")
        }
        for row in rows
    ]
def clear_all_preferences():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM preferences")
    conn.commit()
    conn.close()
# Initialize the database
init_db()

