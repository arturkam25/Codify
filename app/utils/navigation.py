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

    # Kolory sidebara zależne od motywu (ciemny = złoty, jasny = szarość)
    theme = st.session_state.get("theme", "dark")
    if theme == "light":
        sidebar_heading_color = "#1f2937"
        sidebar_border_color = "#e5e7eb"
        sidebar_heading_style = "font-weight: 700; letter-spacing: 2px; text-transform: uppercase;"
    else:
        sidebar_heading_color = "#FFD700"
        sidebar_border_color = "#FFD700"
        sidebar_heading_style = "font-weight: 900; text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8), 0 0 15px rgba(255, 215, 0, 0.6); letter-spacing: 3px; text-transform: uppercase;"

    with st.sidebar:
        st.markdown(f"""
        <div style="
            color: {sidebar_heading_color};
            font-size: 1.8em;
            text-align: center;
            border-bottom: 2px solid {sidebar_border_color};
            padding-bottom: 10px;
            margin-bottom: 15px;
            {sidebar_heading_style}
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
                color: {sidebar_heading_color};
                font-size: 1.2em;
                font-weight: 700;
                text-align: center;
                border-bottom: 1px solid {sidebar_border_color};
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
            
            # API Key input - use query parameter tstreMo force complete widget reset
            widget_key = "api_key_input_widget"
            
            # Check if we need to reset (via query param or session state)
            reset_flag = st.query_params.get("reset_api_key", "false") == "true"
            if reset_flag:
                st.session_state.user_api_key = ""
                if widget_key in st.session_state:
                    del st.session_state[widget_key]
                # Remove query param
                if "reset_api_key" in st.query_params:
                    del st.query_params["reset_api_key"]
            
            # Initialize widget value from user_api_key
            if widget_key not in st.session_state:
                st.session_state[widget_key] = st.session_state.user_api_key
            
            # Main form containing input and buttons
            with st.form("api_key_form", clear_on_submit=False, enter_to_submit=False):
                api_key_input = st.text_input(
                    t(current_lang, "Wprowadź swój klucz API OpenAI", "Enter your OpenAI API key"),
                    value="" if reset_flag else st.session_state[widget_key],
                    type="password",
                    help=None,
                    key=widget_key
                )
                
                col1, col2 = st.columns(2)
            
                with col1:
                    save_clicked = st.form_submit_button(t(current_lang, "💾 Zapisz", "💾 Save"), use_container_width=True)
                
                with col2:
                    remove_clicked = st.form_submit_button(t(current_lang, "🗑️ Usuń", "🗑️ Remove"), use_container_width=True)
            
            # Handle save
            if save_clicked:
                if api_key_input and api_key_input.strip():
                    st.session_state.user_api_key = api_key_input.strip()
                    st.success(t(current_lang, "Klucz API zapisany!", "API key saved!"))
                    st.rerun()
                else:
                    st.warning(t(current_lang, "Wprowadź klucz API", "Please enter an API key"))
            
            # Handle remove - use query parameter to force complete reset
            if remove_clicked:
                st.session_state.user_api_key = ""
                # Delete widget key
                if widget_key in st.session_state:
                    del st.session_state[widget_key]
                # Use query parameter to force widget reset on next render
                st.query_params["reset_api_key"] = "true"
                st.info(t(
                    current_lang,
                    "Klucz API usunięty. Funkcje AI będą niedostępne, dopóki nie podasz nowego klucza.",
                    "API key removed. AI features will be unavailable until you enter a new key."
                ))
                st.rerun()
            
            st.markdown("---")

        # Przełącznik motywu (ciemny / jasny)
        st.markdown(f"""
        <div style="
            color: {sidebar_heading_color};
            font-size: 1em;
            font-weight: 700;
            margin-bottom: 8px;
        ">
            🎨 {t(current_lang, 'MOTYW', 'THEME')}
        </div>
        """, unsafe_allow_html=True)
        theme_labels = {"dark": "🌙 " + t(current_lang, "Ciemny", "Dark"), "light": "☀️ " + t(current_lang, "Jasny", "Light")}
        theme_idx = 0 if st.session_state.get("theme", "dark") == "dark" else 1
        theme_choice = st.radio(
            t(current_lang, "Tło", "Background"),
            options=["dark", "light"],
            format_func=lambda x: theme_labels[x],
            index=theme_idx,
            key="theme_radio",
            horizontal=True,
            label_visibility="collapsed"
        )
        if theme_choice != st.session_state.get("theme", "dark"):
            st.session_state.theme = theme_choice
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
                color: {sidebar_heading_color};
                font-size: 1.8em;
                text-align: center;
                border-bottom: 2px solid {sidebar_border_color};
                padding-bottom: 10px;
                margin-bottom: 15px;
                {sidebar_heading_style}
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

