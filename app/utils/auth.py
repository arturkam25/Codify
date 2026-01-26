# ==============================================================================
# STREAMLIT AUTHENTICATION GUARDS AND SESSION CONTROL
# ==============================================================================

import streamlit as st

def require_login():
    """Blocks access to the current page if the user is not authenticated."""
    if not st.session_state.get("authenticated", False):
        st.warning("Proszę się zalogować, aby uzyskać dostęp do tej strony.")
        st.stop()

    return st.session_state.user

def require_admin():
    """Blocks access if the current user does not have administrative privileges."""
    user = require_login()

    if not user.get("is_admin", False):
        st.error("Odmowa dostępu. Wymagane uprawnienia administratora.")
        st.stop()

    return user

def logout():
    """Logs the user out by clearing session state and redirecting to landing."""
    # Preserve language when logging out
    current_lang = st.query_params.get("lang", st.session_state.get("lang", "pl"))
    st.session_state.authenticated = False
    st.session_state.user = None
    st.query_params.clear()
    st.query_params["page"] = "landing"
    st.query_params["lang"] = current_lang
    st.rerun()

