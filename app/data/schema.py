# ==============================================================================
# DATABASE SCHEMA AND LICENSE KEY UTILITIES
# ==============================================================================

from .db import get_connection
import random
import string

def generate_license_key():
    """Generates a 12-character license key in the format XXXX-XXXX-XXXX."""
    def block():
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{block()}-{block()}-{block()}"

def create_tables():
    """Creates all database tables required by the application."""
    conn = get_connection()
    curr = conn.cursor()
    
    # Users table
    curr.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_admin INTEGER,
            disabled INTEGER,
            role TEXT,
            email TEXT,
            license_key TEXT,
            failed_attempts INTEGER DEFAULT 0,
            recovery_code TEXT
        );
    """)
    
    # Conversations table for chat history
    curr.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT,
            personality TEXT,
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    
    # Messages table for chat messages
    curr.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            usage_data TEXT,
            created_at TEXT,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        );
    """)
    
    # Code translations table
    curr.execute("""
        CREATE TABLE IF NOT EXISTS code_translations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            source_code TEXT,
            translated_code TEXT,
            source_language TEXT,
            target_language TEXT,
            translation_level TEXT,
            source_type TEXT,
            created_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    """)
    
    # Costs table for tracking API usage costs
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
        );
    """)
    
    # Add missing columns for existing databases
    try:
        curr.execute("SELECT failed_attempts FROM users LIMIT 1;")
    except:
        try:
            curr.execute("ALTER TABLE users ADD COLUMN failed_attempts INTEGER DEFAULT 0;")
            conn.commit()
        except:
            pass

    try:
        curr.execute("SELECT recovery_code FROM users LIMIT 1;")
    except:
        try:
            curr.execute("ALTER TABLE users ADD COLUMN recovery_code TEXT;")
            conn.commit()
        except:
            pass
    
    # Add model column to conversations if it doesn't exist
    try:
        curr.execute("SELECT model FROM conversations LIMIT 1;")
    except:
        try:
            curr.execute("ALTER TABLE conversations ADD COLUMN model TEXT DEFAULT 'gpt-4o-mini';")
            conn.commit()
        except:
            pass

    conn.commit()
    conn.close()

