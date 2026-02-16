# ==============================================================================
# DATABASE SCHEMA AND LICENSE KEY UTILITIES
# ==============================================================================

from .db import get_connection, get_db_type
import random
import string

def generate_license_key():
    """Generates a 12-character license key in the format XXXX-XXXX-XXXX."""
    def block():
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"{block()}-{block()}-{block()}"

def create_tables():
    """Creates all database tables required by the application (SQLite or PostgreSQL)."""
    conn = get_connection()
    curr = conn.cursor()
    is_pg = get_db_type() == "postgres"

    if is_pg:
        # PostgreSQL: SERIAL dla auto-increment, bez AUTOINCREMENT
        curr.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
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
        curr.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                name TEXT,
                personality TEXT,
                created_at TEXT,
                updated_at TEXT,
                model TEXT DEFAULT 'gpt-4o-mini'
            );
        """)
        curr.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                conversation_id INTEGER NOT NULL REFERENCES conversations(id),
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                usage_data TEXT,
                created_at TEXT
            );
        """)
        curr.execute("""
            CREATE TABLE IF NOT EXISTS code_translations (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                source_code TEXT,
                translated_code TEXT,
                source_language TEXT,
                target_language TEXT,
                translation_level TEXT,
                source_type TEXT,
                created_at TEXT
            );
        """)
        curr.execute("""
            CREATE TABLE IF NOT EXISTS costs (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                date TEXT NOT NULL,
                cost_usd REAL NOT NULL,
                conversation_id INTEGER,
                translation_id INTEGER,
                created_at TEXT
            );
        """)
    else:
        # SQLite (lokalnie)
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

    # Dodawanie brakujących kolumn (obie bazy)
    for col, defn in [
        ("failed_attempts", "INTEGER DEFAULT 0"),
        ("recovery_code", "TEXT"),
    ]:
        try:
            curr.execute(f"SELECT {col} FROM users LIMIT 1;")
        except Exception:
            try:
                curr.execute(f"ALTER TABLE users ADD COLUMN {col} {defn};")
                conn.commit()
            except Exception:
                pass

    try:
        curr.execute("SELECT model FROM conversations LIMIT 1;")
    except Exception:
        try:
            curr.execute("ALTER TABLE conversations ADD COLUMN model TEXT DEFAULT 'gpt-4o-mini';")
            conn.commit()
        except Exception:
            pass

    conn.commit()
    conn.close()
