# ==============================================================================
# COST TRACKING FOR API USAGE
# ==============================================================================

import json
from datetime import datetime, timedelta
from pathlib import Path
from app.data.db import get_connection

def log_cost(user_id, cost_usd, conversation_id=None, translation_id=None):
    """Logs a cost for a user."""
    conn = get_connection()
    curr = conn.cursor()
    today = datetime.now().strftime("%Y-%m-%d")
    now = datetime.now().isoformat()
    
    try:
        # Create costs table if it doesn't exist
        curr.execute("""
            CREATE TABLE IF NOT EXISTS costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                cost_usd REAL NOT NULL,
                conversation_id INTEGER,
                translation_id INTEGER,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        curr.execute(
            """
            INSERT INTO costs (user_id, date, cost_usd, conversation_id, translation_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, today, cost_usd, conversation_id, translation_id, now)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_daily_costs(user_id, days=60):
    """Gets daily cost summary for a user."""
    conn = get_connection()
    curr = conn.cursor()
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    try:
        # Ensure costs table exists
        curr.execute("""
            CREATE TABLE IF NOT EXISTS costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                cost_usd REAL NOT NULL,
                conversation_id INTEGER,
                translation_id INTEGER,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.commit()
        
        curr.execute(
            """
            SELECT date, SUM(cost_usd) as total
            FROM costs
            WHERE user_id = ? AND date >= ?
            GROUP BY date
            ORDER BY date DESC
            """,
            (user_id, cutoff_date)
        )
        rows = curr.fetchall()
        return {row[0]: round(row[1], 4) for row in rows}
    finally:
        conn.close()

def get_total_cost(user_id):
    """Gets total cost for a user."""
    conn = get_connection()
    curr = conn.cursor()
    try:
        # Ensure costs table exists
        curr.execute("""
            CREATE TABLE IF NOT EXISTS costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                cost_usd REAL NOT NULL,
                conversation_id INTEGER,
                translation_id INTEGER,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.commit()
        
        curr.execute(
            "SELECT SUM(cost_usd) FROM costs WHERE user_id = ?",
            (user_id,)
        )
        result = curr.fetchone()
        return round(result[0] or 0.0, 4)
    finally:
        conn.close()

def get_conversation_cost(conversation_id):
    """Gets total cost for a conversation."""
    conn = get_connection()
    curr = conn.cursor()
    try:
        # Ensure costs table exists
        curr.execute("""
            CREATE TABLE IF NOT EXISTS costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                cost_usd REAL NOT NULL,
                conversation_id INTEGER,
                translation_id INTEGER,
                created_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        conn.commit()
        
        curr.execute(
            "SELECT SUM(cost_usd) FROM costs WHERE conversation_id = ?",
            (conversation_id,)
        )
        result = curr.fetchone()
        return round(result[0] or 0.0, 6)
    finally:
        conn.close()

