# ==============================================================================
# CONVERSATION MANAGEMENT
# ==============================================================================

import json
from datetime import datetime
from app.data.db import get_connection

def create_conversation(user_id, name, personality, model="gpt-4o-mini"):
    """Creates a new conversation for a user."""
    conn = get_connection()
    curr = conn.cursor()
    now = datetime.now().isoformat()
    
    try:
        curr.execute(
            """
            INSERT INTO conversations (user_id, name, personality, model, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (user_id, name, personality, model, now, now)
        )
        conn.commit()
        return curr.lastrowid
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_conversation(conversation_id):
    """Retrieves a conversation by ID."""
    conn = get_connection()
    curr = conn.cursor()
    try:
        curr.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
        row = curr.fetchone()
        if row:
            result = {
                "id": row[0],
                "user_id": row[1],
                "name": row[2],
                "personality": row[3],
                "created_at": row[4],
                "updated_at": row[5] if len(row) > 5 else None
            }
            # Add model if column exists (for backward compatibility)
            if len(row) > 6:
                result["model"] = row[6]
            else:
                result["model"] = "gpt-4o-mini"
            return result
        return None
    finally:
        conn.close()

def get_user_conversations(user_id):
    """Retrieves all conversations for a user."""
    conn = get_connection()
    curr = conn.cursor()
    try:
        curr.execute(
            "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,)
        )
        rows = curr.fetchall()
        return [
            {
                "id": row[0],
                "user_id": row[1],
                "name": row[2],
                "personality": row[3],
                "created_at": row[4],
                "updated_at": row[5]
            }
            for row in rows
        ]
    finally:
        conn.close()

def update_conversation(conversation_id, name=None, personality=None, model=None):
    """Updates a conversation."""
    conn = get_connection()
    curr = conn.cursor()
    now = datetime.now().isoformat()
    
    updates = []
    params = []
    
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if personality is not None:
        updates.append("personality = ?")
        params.append(personality)
    if model is not None:
        updates.append("model = ?")
        params.append(model)
    
    updates.append("updated_at = ?")
    params.append(now)
    params.append(conversation_id)
    
    try:
        curr.execute(
            f"UPDATE conversations SET {', '.join(updates)} WHERE id = ?",
            params
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()

def add_message(conversation_id, role, content, usage_data=None):
    """Adds a message to a conversation."""
    conn = get_connection()
    curr = conn.cursor()
    now = datetime.now().isoformat()
    
    usage_json = json.dumps(usage_data) if usage_data else None
    
    try:
        curr.execute(
            """
            INSERT INTO messages (conversation_id, role, content, usage_data, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, role, content, usage_json, now)
        )
        conn.commit()
        
        # Update conversation's updated_at
        update_conversation(conversation_id)
        
        return curr.lastrowid
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_conversation_messages(conversation_id, limit=None):
    """Retrieves messages for a conversation."""
    conn = get_connection()
    curr = conn.cursor()
    try:
        query = "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC"
        if limit:
            query += f" LIMIT {limit}"
        curr.execute(query, (conversation_id,))
        rows = curr.fetchall()
        messages = []
        for row in rows:
            usage_data = None
            if row[4]:
                try:
                    usage_data = json.loads(row[4])
                except:
                    pass
            messages.append({
                "id": row[0],
                "conversation_id": row[1],
                "role": row[2],
                "content": row[3],
                "usage": usage_data,
                "created_at": row[5]
            })
        return messages
    finally:
        conn.close()

def delete_conversation(conversation_id):
    """Deletes a conversation and all its messages."""
    conn = get_connection()
    curr = conn.cursor()
    try:
        # Delete messages first
        curr.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        # Delete conversation
        curr.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise
    finally:
        conn.close()

