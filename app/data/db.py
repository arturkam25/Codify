# ==============================================================================
# DATABASE CONNECTION CONFIGURATION
# ==============================================================================

import sqlite3
from pathlib import Path

DB_PATH = Path("DATA/codify.db")
DB_PATH.parent.mkdir(exist_ok=True)

def get_connection():
    """Creates and returns a new SQLite database connection."""
    return sqlite3.connect(str(DB_PATH))

