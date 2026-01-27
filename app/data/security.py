# ==============================================================================
# AUTHENTICATION, PASSWORD SECURITY AND RECOVERY UTILITIES
# ==============================================================================

import re
import bcrypt
import random
import string

def validate_password_strength(password):
    """Validates a password against security requirements."""
    checks = {
        "min_length": len(password) >= 8,
        "uppercase": bool(re.search(r"[A-Z]", password)),
        "lowercase": bool(re.search(r"[a-z]", password)),
        "digit": bool(re.search(r"[0-9]", password)),
        "special": bool(
            re.search(r"[!@#$%^&*()_+\-=\[\]{};':\",.<>/?\\|`~]", password)
        )
    }
    return all(checks.values()), checks

def password_feedback(checks):
    """Generates human-readable feedback messages for password validation."""
    messages = []
    if not checks["min_length"]:
        messages.append("Hasło musi mieć co najmniej 8 znaków.")
    if not checks["uppercase"]:
        messages.append("Hasło musi zawierać wielką literę.")
    if not checks["lowercase"]:
        messages.append("Hasło musi zawierać małą literę.")
    if not checks["digit"]:
        messages.append("Hasło musi zawierać cyfrę.")
    if not checks["special"]:
        messages.append("Hasło musi zawierać znak specjalny.")
    return messages

def hash_password(password):
    """Hashes a plaintext password using bcrypt."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

def verify_password(password, hashed):
    """Verifies a plaintext password against a stored bcrypt hash."""
    try:
        # Ensure password is a string
        if not isinstance(password, str):
            password = str(password)
        
        # Strip whitespace from password
        password = password.strip()
        
        # Ensure hashed is bytes (bcrypt requires bytes)
        if isinstance(hashed, str):
            # Strip whitespace from hashed string before encoding
            hashed = hashed.strip()
            hashed_bytes = hashed.encode("utf-8")
        elif isinstance(hashed, bytes):
            hashed_bytes = hashed
        else:
            return False
        
        return bcrypt.checkpw(
            password.encode("utf-8"),
            hashed_bytes
        )
    except Exception as e:
        import sys
        print(f"Error in verify_password: {e}", file=sys.stderr)
        print(f"Password type: {type(password)}, Hashed type: {type(hashed)}", file=sys.stderr)
        return False

def generate_recovery_code():
    """Generates a recovery code in the format XXXX-XXXX-XXXX."""
    parts = []
    for _ in range(3):
        part = "".join(
            random.choice(string.ascii_uppercase + string.digits)
            for _ in range(4)
        )
        parts.append(part)
    return "-".join(parts)

def is_valid_email(email):
    """Validates an email address using basic constraints."""
    if not email or len(email) > 254 or " " in email:
        return False
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))

def authenticate_user(username, password, lang="pl"):
    """Authenticates a user using username and password."""
    from .users import (
        get_user_by_username,
        update_user_failed_attempts,
        lock_user_account
    )

    MAX_ATTEMPTS = 3
    
    # Translation helper
    def t(pl, en):
        return pl if lang == "pl" else en

    user = get_user_by_username(username)

    if not user:
        return False, None, t("Nieprawidłowa nazwa użytkownika lub hasło.", "Invalid username or password.")

    # Handle different number of columns (for backward compatibility)
    # Table has: id, username, password_hash, is_admin, disabled, role, email, license_key, failed_attempts, recovery_code
    user_id = user[0]
    db_username = user[1]
    password_hash = user[2] if len(user) > 2 else None
    is_admin = user[3] if len(user) > 3 else 0
    disabled = user[4] if len(user) > 4 else 0
    role = user[5] if len(user) > 5 else None
    email = user[6] if len(user) > 6 else None
    license_key = user[7] if len(user) > 7 else None
    
    # failed_attempts is at index 8 (if exists)
    if len(user) > 8:
        failed_attempts = user[8] if user[8] is not None else 0
    else:
        failed_attempts = 0
    
    # Ensure failed_attempts is an integer
    try:
        failed_attempts = int(failed_attempts) if failed_attempts is not None else 0
    except (ValueError, TypeError):
        failed_attempts = 0

    # Check if password_hash exists
    if not password_hash:
        return False, None, t("Nieprawidłowa nazwa użytkownika lub hasło.", "Invalid username or password.")

    # Check if account is disabled (but don't reveal this if password is wrong)
    # We'll check this after password verification to avoid information leakage

    # Verify password
    try:
        # Ensure password_hash is a string (not bytes)
        if isinstance(password_hash, bytes):
            password_hash = password_hash.decode("utf-8")
        
        # Strip any whitespace from password_hash (in case of database issues)
        password_hash = password_hash.strip() if password_hash else ""
        
        # Strip whitespace from password input
        password = password.strip() if password else ""
        
        if not password_hash:
            return False, None, t("Nieprawidłowa nazwa użytkownika lub hasło.", "Invalid username or password.")
        
        password_valid = verify_password(password, password_hash)
    except Exception as e:
        # Log the error for debugging
        import sys
        print(f"Password verification error: {e}", file=sys.stderr)
        print(f"Password hash type: {type(password_hash)}", file=sys.stderr)
        print(f"Password hash length: {len(password_hash) if password_hash else 0}", file=sys.stderr)
        # If password verification fails due to error, treat as invalid password
        password_valid = False
    
    if password_valid:
        # Check if account is disabled AFTER password verification (to avoid information leakage)
        if disabled:
            return False, None, t(
                "Twoje konto zostało zablokowane po wielu nieudanych próbach logowania. Skontaktuj się z administratorem lub użyj funkcji odzyskiwania hasła.",
                "Your account has been locked after multiple failed login attempts. Please contact the administrator or use password recovery."
            )
        
        update_user_failed_attempts(user_id, 0)
        
        # If no admin exists, make this user the first admin
        from .users import has_any_admin, make_user_admin
        if not has_any_admin():
            make_user_admin(user_id)
            is_admin = 1
            role = "admin"

        user_data = {
            "id": user_id,
            "username": db_username,
            "is_admin": bool(is_admin),
            "disabled": bool(disabled),
            "role": role,
            "email": email,
            "license_key": license_key
        }

        return True, user_data, t("Logowanie udane.", "Login successful.")

    # Password is invalid - increment failed attempts
    failed_attempts = failed_attempts + 1
    update_user_failed_attempts(user_id, failed_attempts)

    remaining = MAX_ATTEMPTS - failed_attempts

    if remaining <= 0:
        lock_user_account(user_id)
        return False, None, t(
            "Twoje konto zostało zablokowane po 3 nieudanych próbach logowania. Skontaktuj się z administratorem.",
            "Your account has been locked after 3 failed login attempts. Please contact the administrator."
        )

    return False, None, t(
        f"Nieprawidłowe hasło. Pozostało {remaining} prób(y) przed zablokowaniem konta.",
        f"Invalid password. {remaining} attempt(s) remaining before your account is locked."
    )

