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


import sqlite3
from datetime import datetime

# Database connection setup
DB_FILE = "rate_limit.db"

def init_db():
    # Connect to the database (or create it if it doesn't exist)
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # Create the rate_limit table if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rate_limit (
            identifier TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0,
            last_reset TEXT
        )
    ''')

    conn.commit()
    conn.close()

# Initialize the database
init_db()
