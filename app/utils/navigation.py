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
        
        # Check if user is logged in
        user = require_login()
        
        # API Key Configuration Section (only show if user is logged in)
        if user:
            st.markdown(f"""
            <div style="
                color: #FFD700;
                font-size: 1.2em;
                font-weight: 700;
                text-align: center;
                border-bottom: 1px solid #FFD700;
                padding-bottom: 8px;
                margin-bottom: 10px;
            ">
                🔑 {t(current_lang, 'KLUCZ API', 'API KEY')}
            </div>
            """, unsafe_allow_html=True)
            
            # Initialize session state for API key if not exists
            if "user_api_key" not in st.session_state:
                st.session_state.user_api_key = ""
            
            # Show current status
            if st.session_state.user_api_key:
                st.success(t(
                    current_lang,
                    "✓ Używasz własnego klucza API",
                    "✓ Using your own API key"
                ))
            else:
                st.info(t(
                    current_lang,
                    "ℹ Nie wprowadzono klucza API. Funkcje AI będą niedostępne, dopóki nie podasz swojego klucza.",
                    "ℹ No API key set. AI features will be unavailable until you enter your own key."
                ))
            
            # API Key input - use a separate key for widget to avoid conflicts
            widget_key = "api_key_widget_value"
            
            # Initialize widget value from user_api_key only on first render
            if widget_key not in st.session_state:
                st.session_state[widget_key] = st.session_state.user_api_key
            
            # If user_api_key was cleared, sync widget BEFORE creating it
            # This is safe because we're modifying before widget instantiation
            if st.session_state.user_api_key == "" and st.session_state.get(widget_key, "") != "":
                st.session_state[widget_key] = ""
            
            # Create input field
            api_key_input = st.text_input(
                t(current_lang, "Wprowadź swój klucz API OpenAI", "Enter your OpenAI API key"),
                value=st.session_state[widget_key],
                type="password",
                help=t(current_lang, 
                       "Wprowadź swój klucz API OpenAI aby używać aplikacji na własnym koncie. Klucz jest przechowywany tylko w tej sesji.",
                       "Enter your OpenAI API key to use the app with your own account. The key is stored only in this session."),
                key=widget_key
            )
            
            col1, col2 = st.columns(2)
            
            # Save button - separate form to avoid conflicts
            with col1:
                with st.form("save_api_key_form", clear_on_submit=False):
                    save_clicked = st.form_submit_button(t(current_lang, "💾 Zapisz", "💾 Save"), use_container_width=True)
                    if save_clicked:
                        if api_key_input and api_key_input.strip():
                            st.session_state.user_api_key = api_key_input.strip()
                            st.success(t(current_lang, "Klucz API zapisany!", "API key saved!"))
                            st.rerun()
                        else:
                            st.warning(t(current_lang, "Wprowadź klucz API", "Please enter an API key"))
            
            # Remove button - separate form to avoid conflicts  
            with col2:
                remove_clicked = st.button(t(current_lang, "🗑️ Usuń", "🗑️ Remove"), use_container_width=True, key="remove_api_key")
                if remove_clicked:
                    # Clear user_api_key (safe - not a widget key)
                    st.session_state.user_api_key = ""
                    # Widget value will be synced on next render (lines 118-119)
                    st.info(t(
                        current_lang,
                        "Klucz API usunięty. Funkcje AI będą niedostępne, dopóki nie podasz nowego klucza.",
                        "API key removed. AI features will be unavailable until you enter a new key."
                    ))
                    st.rerun()
            
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
        if user and user.get("is_admin", False):
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

