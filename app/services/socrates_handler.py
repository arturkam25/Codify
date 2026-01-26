# ==============================================================================
# SOCRATES PERSONALITY HANDLER
# ==============================================================================

def check_socrates_response(user_message, conversation_messages):
    """
    Checks if user has said 'nie wiem' three times in a row.
    Returns True if we should give direct answer, False if we should ask questions.
    """
    # Include current message in check
    all_messages = conversation_messages + [{"role": "user", "content": user_message}]
    
    # Look at last few messages to count "nie wiem"
    recent_messages = all_messages[-6:] if len(all_messages) > 6 else all_messages
    
    # Count consecutive "nie wiem" from the end
    count = 0
    for msg in reversed(recent_messages):
        if msg["role"] == "user":
            content_lower = msg["content"].lower().strip()
            # Check for variations of "nie wiem"
            if any(phrase in content_lower for phrase in ["nie wiem", "nie wiem.", "nie wiem!", "nie wiem?", "dont know", "i don't know", "nie wiem,"]):
                count += 1
            else:
                break  # Break on first non-"nie wiem" message
    
    return count >= 3

def should_ask_question(user_message, conversation_messages):
    """Determines if we should ask a question (Socrates mode) or give direct answer."""
    # If user has said "nie wiem" three times, give direct answer
    if check_socrates_response(user_message, conversation_messages):
        return False
    
    # Otherwise, ask questions
    return True

