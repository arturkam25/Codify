# ==============================================================================
# STREAMLIT UI LAYOUT AND NAVIGATION CONTROLS
# ==============================================================================

import streamlit as st

def hide_default_streamlit_menu():
    """Hides the default Streamlit pages navigation."""
    st.markdown(
        """
        <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def hide_sidebar_completely():
    """Completely hides the Streamlit sidebar."""
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] {
            display: none;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def render_navigation_sidebar():
    """Renders a custom navigation sidebar."""
    from app.utils.auth import require_login, logout
    
    # Translation helper function
    def t(lang: str, pl: str, en: str) -> str:
        """Translation helper."""
        return pl if lang == "pl" else en
    
    # Get current language from query params or session state
    try:
        current_lang = st.query_params.get("lang", "pl")
        if current_lang not in ["pl", "en"]:
            current_lang = "pl"
    except:
        current_lang = st.session_state.get("lang", "pl")
    
    # Store language in session state as backup
    st.session_state["lang"] = current_lang

    with st.sidebar:
        st.markdown(f"""
        <div style="
            color: #FFD700;
            font-size: 1.8em;
            font-weight: 900;
            text-align: center;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8), 0 0 15px rgba(255, 215, 0, 0.6), 0 0 30px rgba(255, 215, 0, 0.4);
            letter-spacing: 3px;
            text-transform: uppercase;
            border-bottom: 2px solid #FFD700;
            padding-bottom: 10px;
            margin-bottom: 15px;
        ">
            🧭 {t(current_lang, 'NAWIGACJA', 'NAVIGATION')}
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")

        if st.button(t(current_lang, "Strona główna", "Home"), use_container_width=True, key="nav_home"):
            st.query_params["page"] = "dashboard"
            st.query_params["lang"] = current_lang
            st.rerun()

        if st.button(t(current_lang, "💬 Chat z AI", "💬 Chat with AI"), use_container_width=True, key="nav_chat"):
            st.query_params["page"] = "chat"
            st.query_params["lang"] = current_lang
            st.rerun()

        if st.button(t(current_lang, "📸 Tłumaczenie kodu", "📸 Code Translation"), use_container_width=True, key="nav_image"):
            st.query_params["page"] = "image_translate"
            st.query_params["lang"] = current_lang
            st.rerun()

        if st.button(t(current_lang, "📝 Konwersja kodu między językami", "📝 Code Conversion Between Languages"), use_container_width=True, key="nav_text"):
            st.query_params["page"] = "text_translate"
            st.query_params["lang"] = current_lang
            st.rerun()

        if st.button(t(current_lang, "💰 Koszty i historia", "💰 Costs and History"), use_container_width=True, key="nav_costs"):
            st.query_params["page"] = "costs"
            st.query_params["lang"] = current_lang
            st.rerun()

        # Admin only section
        user = require_login()
        if user.get("is_admin", False):
            st.markdown("---")
            st.markdown(f"""
            <div style="
                color: #FFD700;
                font-size: 1.8em;
                font-weight: 900;
                text-align: center;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8), 0 0 15px rgba(255, 215, 0, 0.6), 0 0 30px rgba(255, 215, 0, 0.4);
                letter-spacing: 3px;
                text-transform: uppercase;
                border-bottom: 2px solid #FFD700;
                padding-bottom: 10px;
                margin-bottom: 15px;
            ">
                🔐 {t(current_lang, 'ADMINISTRACJA', 'ADMINISTRATION')}
            </div>
            """, unsafe_allow_html=True)
            if st.button(t(current_lang, "👤 Zarządzanie użytkownikami", "👤 User Management"), use_container_width=True, key="nav_admin_users"):
                st.query_params["page"] = "admin_users"
                st.query_params["lang"] = current_lang
                st.rerun()

        st.markdown("---")

        if st.button(t(current_lang, "🚪 Wyloguj", "🚪 Logout"), use_container_width=True, key="nav_logout"):
            logout()

