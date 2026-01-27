# ==============================================================================
# USERS DATA ACCESS AND SECURITY OPERATIONS
# ==============================================================================

from .db import get_connection
from .schema import generate_license_key

def _bool(value):
    """Converts None or string 'None' to integer 0."""
    return 0 if value in (None, "None") else int(value)

def create_user(username, password_hash, is_admin, disabled, role, email, license_key):
    """Creates a new user record and returns its database ID."""
    conn = get_connection()
    curr = conn.cursor()
    sql = """
        INSERT INTO users
        (username, password_hash, is_admin, disabled, role, email, license_key)
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """
    try:
        curr.execute(
            sql,
            (username, password_hash, is_admin, disabled, role, email, license_key)
        )
        conn.commit()
        return curr.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_user_by_id(user_id):
    """Retrieves a user record by its unique ID."""
    conn = get_connection()
    curr = conn.cursor()
    try:
        curr.execute("SELECT * FROM users WHERE id = ?;", (user_id,))
        return curr.fetchone()
    finally:
        conn.close()

def get_user_by_username(username):
    """Retrieves a user record by username."""
    conn = get_connection()
    curr = conn.cursor()
    try:
        try:
            curr.execute(
                "ALTER TABLE users ADD COLUMN failed_attempts INTEGER DEFAULT 0;"
            )
            conn.commit()
        except:
            pass

        try:
            curr.execute(
                "ALTER TABLE users ADD COLUMN recovery_code TEXT;"
            )
            conn.commit()
        except:
            pass

        curr.execute("SELECT * FROM users WHERE username = ?;", (username,))
        return curr.fetchone()
    finally:
        conn.close()

def has_any_admin():
    """Checks if there is any admin user in the database."""
    conn = get_connection()
    curr = conn.cursor()
    try:
        curr.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1")
        count = curr.fetchone()[0]
        return count > 0
    finally:
        conn.close()

def make_user_admin(user_id):
    """Makes a user an administrator."""
    conn = get_connection()
    curr = conn.cursor()
    try:
        curr.execute(
            "UPDATE users SET is_admin = 1, role = 'admin' WHERE id = ?",
            (user_id,)
        )
        conn.commit()
        return True
    except Exception as e:
        conn.rollback()
        return False
    finally:
        conn.close()

def get_all_users():
    """Retrieves all users from the database."""
    conn = get_connection()
    curr = conn.cursor()
    try:
        curr.execute("SELECT * FROM users ORDER BY is_admin DESC, id ASC")
        return curr.fetchall()
    finally:
        conn.close()

def get_user_by_email(email):
    """Retrieves a user record by email address."""
    conn = get_connection()
    curr = conn.cursor()
    try:
        curr.execute("SELECT * FROM users WHERE email = ?", (email.lower(),))
        return curr.fetchone()
    finally:
        conn.close()

def update_user_failed_attempts(user_id, failed_attempts):
    """Updates the number of failed login attempts for a user."""
    conn = get_connection()
    curr = conn.cursor()
    try:
        # Ensure column exists
        try:
            curr.execute(
                "ALTER TABLE users ADD COLUMN failed_attempts INTEGER DEFAULT 0;"
            )
            conn.commit()
        except:
            pass

        # Ensure failed_attempts is an integer
        failed_attempts_int = int(failed_attempts) if failed_attempts is not None else 0
        
        curr.execute(
            "UPDATE users SET failed_attempts = ? WHERE id = ?",
            (failed_attempts_int, user_id)
        )
        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"ERROR update_user_failed_attempts: {e}")
        raise
    finally:
        conn.close()

def lock_user_account(user_id):
    """Locks a user account after repeated failed login attempts. Prevents locking the first admin."""
    # Protect first admin from being locked
    if is_first_admin(user_id):
        return False, "Nie można zablokować konta pierwszego administratora (super admin)."
    
    conn = get_connection()
    curr = conn.cursor()
    try:
        curr.execute(
            "UPDATE users SET disabled = 1, failed_attempts = 3 WHERE id = ?",
            (user_id,)
        )
        conn.commit()
        return True, "Konto użytkownika zostało zablokowane."
    except Exception as e:
        conn.rollback()
        print(f"Error locking account: {e}")
        return False, f"Błąd podczas blokowania konta: {e}"
    finally:
        conn.close()

def generate_recovery_code_for_user(user_id):
    """Generates and stores a recovery code for a user."""
    from .security import generate_recovery_code
    recovery_code = generate_recovery_code()
    conn = get_connection()
    curr = conn.cursor()
    try:
        curr.execute(
            "UPDATE users SET recovery_code = ? WHERE id = ?",
            (recovery_code, user_id)
        )
        conn.commit()
        return recovery_code
    except Exception:
        conn.rollback()
        return None
    finally:
        conn.close()

def reset_password_with_recovery(username, email, recovery_code, new_password):
    """Resets a user's password using a recovery code or license key."""
    from .security import validate_password_strength, password_feedback, hash_password, verify_password

    valid, checks = validate_password_strength(new_password)
    if not valid:
        return False, password_feedback(checks)

    user = get_user_by_username(username)
    if not user:
        return False, "Użytkownik nie został znaleziony."

    if len(user) >= 10:
        (
            user_id,
            _,
            password_hash,
            _,
            _,
            _,
            db_email,
            license_key,
            _,
            db_recovery_code
        ) = user
    else:
        (
            user_id,
            _,
            password_hash,
            _,
            _,
            _,
            db_email,
            license_key
        ) = user
        db_recovery_code = None

    if db_email.lower() != email.lower():
        return False, "Email nie pasuje."

    recovery_code_upper = recovery_code.upper().strip()
    license_key_upper = license_key.upper().strip() if license_key else ""
    db_recovery_code_upper = db_recovery_code.upper().strip() if db_recovery_code else ""

    if (
        recovery_code_upper != db_recovery_code_upper
        and recovery_code_upper != license_key_upper
    ):
        return False, "Nieprawidłowy kod odzyskiwania lub klucz licencyjny."

    if verify_password(new_password, password_hash):
        return False, "Nowe hasło nie może być takie samo jak stare hasło."

    new_password_hash = hash_password(new_password)
    conn = get_connection()
    curr = conn.cursor()
    try:
        curr.execute(
            """
            UPDATE users SET
                password_hash = ?,
                failed_attempts = 0,
                disabled = 0
            WHERE id = ?
            """,
            (new_password_hash, user_id)
        )
        conn.commit()
        return True, "Hasło zostało zresetowane pomyślnie."
    except Exception as e:
        conn.rollback()
        return False, f"Błąd bazy danych: {e}"
    finally:
        conn.close()

def create_user_secure(username, password, is_admin, disabled, role, email):
    """Creates a new user with full validation, hashing and recovery code generation."""
    from .security import (
        is_valid_email,
        generate_recovery_code,
        validate_password_strength,
        password_feedback,
        hash_password
    )

    if email and not is_valid_email(email):
        return False, "Nieprawidłowy format email."

    valid, checks = validate_password_strength(password)
    if not valid:
        return False, password_feedback(checks)

    password_hash = hash_password(password)
    license_key = generate_license_key()
    recovery_code = generate_recovery_code()

    conn = get_connection()
    curr = conn.cursor()
    sql = """
        INSERT INTO users
        (username, password_hash, is_admin, disabled, role, email, license_key, failed_attempts, recovery_code)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
    """
    try:
        curr.execute(
            sql,
            (
                username,
                password_hash,
                _bool(is_admin),
                _bool(disabled),
                role,
                email.lower() if email else "",
                license_key,
                recovery_code
            )
        )
        conn.commit()
        return True, (
            f"Użytkownik '{username}' został utworzony pomyślnie.\n"
            f"Klucz licencyjny: {license_key}\n"
            f"Kod odzyskiwania: {recovery_code}"
        )
    except Exception as e:
        conn.rollback()
        return False, f"Błąd bazy danych: {e}"
    finally:
        conn.close()

def register_user_public(username, password, email):
    """Public-facing user registration function."""
    success, message = create_user_secure(
        username=username,
        password=password,
        is_admin=0,
        disabled=0,
        role="user",
        email=email
    )

    if not success:
        return False, message

    license_line = None
    for line in message.splitlines():
        if "Klucz licencyjny:" in line:
            license_line = line.strip()
            break

    if not license_line:
        return False, "Konto zostało utworzone, ale nie można było pobrać klucza licencyjnego."

    return True, license_line

def update_user(user_id, username, password=None, is_admin=0, disabled=0, role="user", email="", license_key=None):
    """Updates an existing user record. Prevents disabling or removing admin status from the first admin."""
    from .security import validate_password_strength, password_feedback, hash_password
    
    # Protect first admin from being disabled or having admin status removed
    if is_first_admin(user_id):
        # First admin cannot be disabled
        if disabled == 1:
            return False, "Nie można wyłączyć konta pierwszego administratora (super admin)."
        # First admin cannot lose admin status
        if is_admin == 0:
            return False, "Nie można usunąć uprawnień administratora pierwszemu administratorowi (super admin)."
    
    conn = get_connection()
    curr = conn.cursor()

    if password:
        valid, checks = validate_password_strength(password)
        if not valid:
            conn.close()
            return False, password_feedback(checks)
        password_hash = hash_password(password)
    else:
        curr.execute(
            "SELECT password_hash FROM users WHERE id = ?",
            (user_id,)
        )
        result = curr.fetchone()
        if not result:
            conn.close()
            return False, "Użytkownik nie został znaleziony."
        password_hash = result[0]

    sql = """
        UPDATE users SET
            username = ?,
            password_hash = ?,
            is_admin = ?,
            disabled = ?,
            role = ?,
            email = ?,
            license_key = ?
        WHERE id = ?
    """
    try:
        curr.execute(
            sql,
            (
                username,
                password_hash,
                _bool(is_admin),
                _bool(disabled) if not is_first_admin(user_id) else 0,  # Force disabled=0 for first admin
                role,
                email,
                license_key,
                user_id
            )
        )
        conn.commit()
        return True, "Użytkownik zaktualizowany."
    except Exception as e:
        conn.rollback()
        return False, f"Błąd bazy danych: {e}"
    finally:
        conn.close()

def get_first_admin_id():
    """Returns the ID of the first admin (super admin) - the admin with the lowest ID."""
    conn = get_connection()
    curr = conn.cursor()
    try:
        curr.execute("SELECT id FROM users WHERE is_admin = 1 ORDER BY id ASC LIMIT 1")
        result = curr.fetchone()
        return result[0] if result else None
    finally:
        conn.close()

def is_first_admin(user_id):
    """Checks if a user is the first admin (super admin)."""
    first_admin_id = get_first_admin_id()
    return first_admin_id is not None and user_id == first_admin_id

def delete_user(user_id):
    """Deletes a user record by ID. Prevents deletion of the first admin (super admin)."""
    # Check if trying to delete the first admin
    if is_first_admin(user_id):
        return False, "Nie można usunąć pierwszego administratora (super admin). Ten użytkownik jest chroniony przed usunięciem."
    
    conn = get_connection()
    curr = conn.cursor()
    try:
        curr.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return True, "Użytkownik usunięty."
    except Exception as e:
        conn.rollback()
        return False, f"Błąd bazy danych: {e}"
    finally:
        conn.close()

def unlock_user_account(user_id):
    """Unlocks a user account and resets failed login attempts."""
    conn = get_connection()
    curr = conn.cursor()
    try:
        curr.execute(
            "UPDATE users SET disabled = 0, failed_attempts = 0 WHERE id = ?",
            (user_id,)
        )
        conn.commit()
        return True, "Konto użytkownika zostało odblokowane."
    except Exception as e:
        conn.rollback()
        return False, f"Błąd bazy danych: {e}"
    finally:
        conn.close()

