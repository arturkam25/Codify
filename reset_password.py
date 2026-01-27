#!/usr/bin/env python3
# ==============================================================================
# EMERGENCY PASSWORD RESET SCRIPT
# ==============================================================================
# This script allows you to reset a user's password directly in the database
# without needing to log in as admin.
#
# Usage:
#   python reset_password.py <username> <new_password>
#
# Example:
#   python reset_password.py admin NoweHaslo123!
# ==============================================================================

import sys
from pathlib import Path
from app.data.db import get_connection
from app.data.security import hash_password, validate_password_strength, password_feedback

def reset_user_password(username, new_password):
    """Resets a user's password and unlocks their account."""
    # Validate password strength
    valid, checks = validate_password_strength(new_password)
    if not valid:
        print("❌ Hasło nie spełnia wymagań bezpieczeństwa:")
        for msg in password_feedback(checks):
            print(f"   - {msg}")
        return False
    
    # Hash the new password
    password_hash = hash_password(new_password)
    
    # Update database
    conn = get_connection()
    curr = conn.cursor()
    
    try:
        # Check if user exists
        curr.execute("SELECT id, username, disabled FROM users WHERE username = ?", (username,))
        user = curr.fetchone()
        
        if not user:
            print(f"❌ Użytkownik '{username}' nie został znaleziony w bazie danych.")
            return False
        
        user_id, db_username, disabled = user
        
        # Update password and unlock account
        curr.execute(
            """
            UPDATE users SET
                password_hash = ?,
                failed_attempts = 0,
                disabled = 0
            WHERE id = ?
            """,
            (password_hash, user_id)
        )
        conn.commit()
        
        print(f"✅ Hasło dla użytkownika '{username}' zostało zresetowane.")
        print(f"✅ Konto zostało odblokowane.")
        print(f"\nMożesz teraz zalogować się używając:")
        print(f"   Nazwa użytkownika: {username}")
        print(f"   Hasło: {new_password}")
        
        return True
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Błąd podczas resetowania hasła: {e}")
        return False
    finally:
        conn.close()

def list_users():
    """Lists all users in the database."""
    conn = get_connection()
    curr = conn.cursor()
    
    try:
        curr.execute("SELECT id, username, email, is_admin, disabled, failed_attempts FROM users ORDER BY id")
        users = curr.fetchall()
        
        if not users:
            print("❌ Brak użytkowników w bazie danych.")
            return
        
        print("\n📋 Lista użytkowników:")
        print("-" * 80)
        print(f"{'ID':<5} {'Username':<20} {'Email':<30} {'Admin':<8} {'Status':<15}")
        print("-" * 80)
        
        for user in users:
            user_id, username, email, is_admin, disabled, failed_attempts = user
            email = email or "(brak)"
            admin_status = "Tak" if is_admin else "Nie"
            
            if disabled:
                status = f"🔒 Zablokowane ({failed_attempts} prób)"
            else:
                status = "✅ Aktywne"
            
            print(f"{user_id:<5} {username:<20} {email:<30} {admin_status:<8} {status:<15}")
        
        print("-" * 80)
        
    except Exception as e:
        print(f"❌ Błąd podczas pobierania listy użytkowników: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("=" * 80)
    print("🔐 EMERGENCY PASSWORD RESET TOOL")
    print("=" * 80)
    print()
    
    if len(sys.argv) == 1:
        # No arguments - show help and list users
        print("Użycie:")
        print("  python reset_password.py <username> <new_password>")
        print()
        print("Przykład:")
        print("  python reset_password.py admin NoweHaslo123!")
        print()
        list_users()
        sys.exit(0)
    
    if len(sys.argv) != 3:
        print("❌ Nieprawidłowa liczba argumentów.")
        print()
        print("Użycie:")
        print("  python reset_password.py <username> <new_password>")
        print()
        print("Przykład:")
        print("  python reset_password.py admin NoweHaslo123!")
        sys.exit(1)
    
    username = sys.argv[1]
    new_password = sys.argv[2]
    
    print(f"🔄 Resetowanie hasła dla użytkownika: {username}")
    print()
    
    if reset_user_password(username, new_password):
        sys.exit(0)
    else:
        sys.exit(1)
