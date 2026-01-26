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
    return bcrypt.checkpw(
        password.encode("utf-8"),
        hashed.encode("utf-8")
    )

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

    if len(user) >= 9:
        (
            user_id,
            db_username,
            password_hash,
            is_admin,
            disabled,
            role,
            email,
            license_key,
            failed_attempts
        ) = user[:9]
    else:
        (
            user_id,
            db_username,
            password_hash,
            is_admin,
            disabled,
            role,
            email,
            license_key
        ) = user[:8]
        failed_attempts = 0

    if disabled:
        return False, None, t(
            "Twoje konto zostało zablokowane po wielu nieudanych próbach logowania. Skontaktuj się z administratorem.",
            "Your account has been locked after multiple failed login attempts. Please contact the administrator."
        )

    if verify_password(password, password_hash):
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

    failed_attempts = (failed_attempts or 0) + 1
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

