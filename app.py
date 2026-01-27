# ==============================================================================
# CODIFY - APPLICATION FOR CODE TRANSLATION
# ==============================================================================

import base64
import io
from pathlib import Path
import streamlit as st
from app.data.schema import create_tables
from app.data.security import authenticate_user, is_valid_email
from app.data.users import register_user_public, reset_password_with_recovery, get_user_by_email
from app.utils.auth import require_login, logout
from app.utils.navigation import hide_sidebar_completely, hide_default_streamlit_menu, render_navigation_sidebar
from app.services.conversations import (
    create_conversation, get_conversation, get_user_conversations,
    add_message, get_conversation_messages, update_conversation, delete_conversation
)
from app.services.ai_service import (
    chat_completion, translate_code, explain_code_from_image,
    transcribe_audio, text_to_speech, calculate_cost, DEFAULT_MODEL
)
from audio_recorder_streamlit import audio_recorder
from app.services.cost_tracking import log_cost, get_daily_costs, get_total_cost, get_conversation_cost
from app.services.personalities import get_personality, list_personalities, DEFAULT_PERSONALITY

# Initialize database
create_tables()

# Page configuration
st.set_page_config(page_title="Codify", layout="wide", page_icon="💻")

VIDEO_PATH = "landing.mp4"
LOGO_PATH = "logo.png"

# ==============================================================================
# HELPERS
# ==============================================================================

@st.cache_data
def file_b64(path: str) -> str:
    """Converts file to base64 string."""
    return base64.b64encode(Path(path).read_bytes()).decode("utf-8")

def t(lang: str, pl: str, en: str) -> str:
    """Translation helper."""
    return pl if lang == "pl" else en

def get_qp():
    """Gets query parameters."""
    try:
        qp = dict(st.query_params)
        return {k: (v if isinstance(v, str) else v[0]) for k, v in qp.items()}
    except Exception:
        qp = st.experimental_get_query_params()
        return {k: v[0] for k, v in qp.items()}

def get_user_api_key():
    """Gets user API key from session state if available."""
    return st.session_state.get("user_api_key", None)

def set_qp(**kwargs):
    """Sets query parameters."""
    try:
        # Preserve language if not explicitly set
        current_lang = st.query_params.get("lang", st.session_state.get("lang", "pl"))
        if "lang" not in kwargs:
            kwargs["lang"] = current_lang
        
        st.query_params.clear()
        for k, v in kwargs.items():
            st.query_params[k] = v
        
        # Update session state
        if "lang" in kwargs:
            st.session_state["lang"] = kwargs["lang"]
    except Exception:
        # Preserve language if not explicitly set
        current_lang = st.session_state.get("lang", "pl")
        if "lang" not in kwargs:
            kwargs["lang"] = current_lang
        st.experimental_set_query_params(**kwargs)
        if "lang" in kwargs:
            st.session_state["lang"] = kwargs["lang"]

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None
if "show_forgot_password" not in st.session_state:
    st.session_state.show_forgot_password = False
if "user_api_key" not in st.session_state:
    st.session_state.user_api_key = ""

# Get routing
qp = get_qp()
page = qp.get("page", "landing")
lang = qp.get("lang", st.session_state.get("lang", "pl"))
if lang not in ["pl", "en"]:
    lang = "pl"
# Store language in session state as backup
st.session_state["lang"] = lang

# ==============================================================================
# LANDING PAGE
# ==============================================================================

if page == "landing":
    hide_sidebar_completely()
    
    if not Path(VIDEO_PATH).exists():
        st.error(t(lang, f"Brak pliku: {VIDEO_PATH}", f"File not found: {VIDEO_PATH}"))
        st.stop()
    if not Path(LOGO_PATH).exists():
        st.error(t(lang, f"Brak pliku: {LOGO_PATH}", f"File not found: {LOGO_PATH}"))
        st.stop()

    video_b64 = file_b64(VIDEO_PATH)
    logo_b64 = file_b64(LOGO_PATH)

    st.markdown(
        f"""
        <style>
          section.main > div {{ padding-top: 0rem; }}
          header {{ visibility: hidden; height: 0; }}
          .stApp {{ background: transparent; }}

          .video-bg {{
            position: fixed; inset: 0;
            z-index: -3;
            overflow: hidden;
          }}
          .video-bg video {{
            width: 100%;
            height: 100%;
            object-fit: cover;
          }}
          .dim {{
            position: fixed; inset: 0;
            background: rgba(0,0,0,0.55);
            z-index: -2;
          }}

          .logo {{
            position: fixed;
            top: 22px; left: 22px;
            width: 25vw; max-width: 240px; min-width: 140px;
            z-index: 10;
            transform-origin: top left;
            animation: grow 900ms ease-out 0ms both;
          }}
          @keyframes grow {{
            0%   {{ transform: scale(0.15); opacity: 0; filter: blur(6px); }}
            60%  {{ transform: scale(1.08); opacity: 1; filter: blur(0px); }}
            100% {{ transform: scale(1.0);  opacity: 1; }}
          }}

          .lang {{
            position: fixed;
            top: 24px; right: 24px;
            z-index: 10;
          }}
          .pill {{
            padding: 20px 30px;
            border-radius: 999px;
            background: rgba(212,175,55,0.15);
            border: 2px solid #D4AF37;
            color: #D4AF37;
            font-size: 28px;
            font-weight: 900;
            text-decoration: none;
            user-select: none;
          }}        

          .center {{
            position: fixed; inset: 0;
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 9;
          }}
          .card {{
            width: min(760px, 92vw);
            padding: 28px;
            border-radius: 18px;
            background: rgba(0,0,0,0.40);
            backdrop-filter: blur(10px);
          }}
          .title {{
            color: #fff;
            font-size: 32px;
            font-weight: 800;
            margin: 0 0 10px 0;
          }}
          .subtitle {{
            color: rgba(255,255,255,0.85);
            margin: 0 0 18px 0;
            font-size: 16px;
          }}
          .btnrow {{
            display: flex;
            gap: 16px;
          }}
          .btn {{
            flex: 1;
            display: inline-block;
            text-align: center;
            padding: 16px 18px;
            border-radius: 14px;
            background: #D4AF37;
            color: #0b0b0b;
            font-size: 28px;
            font-weight: 900;
            text-decoration: none;
          }}
        </style>

        <div class="video-bg">
          <video autoplay muted loop playsinline preload="auto">
            <source src="data:video/mp4;base64,{video_b64}" type="video/mp4">
          </video>
        </div>
        <div class="dim"></div>

        <img class="logo" src="data:image/png;base64,{logo_b64}" />

        <div class="lang">
          <a class="pill" target="_self" href="?page=landing&lang={"en" if lang=="pl" else "pl"}">
            {"PL" if lang=="pl" else "EN"}
          </a>
        </div>

        <div class="center">
          <div class="card">
            <div class="title">{t(lang, "Witaj w Codify", "Welcome to Codify")}</div>
            <div class="subtitle">{t(lang, "Zrozum swój kod szybciej.", "Understand your code faster.")}</div>
            <div class="btnrow">
              <a class="btn" target="_self" href="?page=login&lang={lang}">{t(lang, "Zaloguj", "Log in")}</a>
              <a class="btn" target="_self" href="?page=register&lang={lang}">{t(lang, "Zarejestruj", "Register")}</a>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ==============================================================================
# LOGIN PAGE
# ==============================================================================

elif page == "login":
    hide_sidebar_completely()
    
    # Login page styling with gold/yellow theme
    st.markdown("""
        <style>
        /* Login Page Background */
        .stApp {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f1419 100%);
        }
        
        /* Login Page Title */
        h1 {
            color: #D4AF37 !important;
            text-shadow: 0 0 15px rgba(212, 175, 55, 0.5);
            font-weight: 900;
        }
        
        /* Horizontal Rule */
        hr {
            border-color: rgba(212, 175, 55, 0.3);
            margin: 20px 0;
        }
        
        /* Form Container Styling */
        .stForm {
            background: rgba(14, 17, 23, 0.6);
            border: 2px solid rgba(212, 175, 55, 0.3);
            border-radius: 15px;
            padding: 30px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        
        /* Text Inputs */
        .stTextInput > div > div > input {
            background: rgba(14, 17, 23, 0.8) !important;
            border: 2px solid rgba(212, 175, 55, 0.3) !important;
            border-radius: 10px !important;
            color: #ffffff !important;
            padding: 12px 15px !important;
            transition: all 0.3s ease !important;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #D4AF37 !important;
            box-shadow: 0 0 15px rgba(212, 175, 55, 0.4) !important;
            outline: none !important;
        }
        
        .stTextInput > div > div > input::placeholder {
            color: rgba(255, 255, 255, 0.5) !important;
        }
        
        /* Input Labels */
        .stTextInput > label {
            color: #D4AF37 !important;
            font-weight: 700 !important;
            font-size: 16px !important;
            margin-bottom: 8px !important;
        }
        
        /* Buttons - Premium Custom Style */
        .stButton > button {
            background: linear-gradient(135deg, #D4AF37 0%, #B8941F 50%, #9A7A1A 100%) !important;
            color: #0b0b0b !important;
            border: none !important;
            border-radius: 25px !important;
            font-weight: 800 !important;
            font-size: 16px !important;
            padding: 14px 28px !important;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
            box-shadow: 0 8px 20px rgba(212, 175, 55, 0.4), 
                        0 4px 8px rgba(0, 0, 0, 0.3),
                        inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
            position: relative !important;
            overflow: hidden !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
            width: 100% !important;
        }
        
        .stButton > button::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
            transition: left 0.5s;
        }
        
        .stButton > button:hover::before {
            left: 100%;
        }
        
        .stButton > button:hover {
            background: linear-gradient(135deg, #E5C158 0%, #D4AF37 50%, #B8941F 100%) !important;
            box-shadow: 0 12px 30px rgba(212, 175, 55, 0.6), 
                        0 6px 12px rgba(0, 0, 0, 0.4),
                        inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
            transform: translateY(-3px) scale(1.02) !important;
        }
        
        .stButton > button:active {
            transform: translateY(-1px) scale(0.98) !important;
            box-shadow: 0 4px 12px rgba(212, 175, 55, 0.4), 
                        0 2px 4px rgba(0, 0, 0, 0.3) !important;
        }
        
        /* Form Submit Button */
        button[type="submit"] {
            background: linear-gradient(135deg, #D4AF37 0%, #B8941F 50%, #9A7A1A 100%) !important;
            color: #0b0b0b !important;
            border: none !important;
            border-radius: 25px !important;
            font-weight: 800 !important;
            font-size: 16px !important;
            padding: 14px 28px !important;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
            box-shadow: 0 8px 20px rgba(212, 175, 55, 0.4), 
                        0 4px 8px rgba(0, 0, 0, 0.3),
                        inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
            position: relative !important;
            overflow: hidden !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
        }
        
        button[type="submit"]::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
            transition: left 0.5s;
        }
        
        button[type="submit"]:hover::before {
            left: 100%;
        }
        
        button[type="submit"]:hover {
            background: linear-gradient(135deg, #E5C158 0%, #D4AF37 50%, #B8941F 100%) !important;
            box-shadow: 0 12px 30px rgba(212, 175, 55, 0.6), 
                        0 6px 12px rgba(0, 0, 0, 0.4),
                        inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
            transform: translateY(-3px) scale(1.02) !important;
        }
        
        button[type="submit"]:active {
            transform: translateY(-1px) scale(0.98) !important;
            box-shadow: 0 4px 12px rgba(212, 175, 55, 0.4), 
                        0 2px 4px rgba(0, 0, 0, 0.3) !important;
        }
        
        /* Error Messages */
        .stAlert {
            background: rgba(244, 67, 54, 0.1) !important;
            border-left: 4px solid #F44336 !important;
            border-radius: 8px !important;
        }
        
        /* Back Button Special Styling */
        button[kind="secondary"] {
            background: rgba(14, 17, 23, 0.8) !important;
            color: #D4AF37 !important;
            border: 2px solid rgba(212, 175, 55, 0.3) !important;
        }
        
        button[kind="secondary"]:hover {
            background: rgba(212, 175, 55, 0.1) !important;
            border-color: #D4AF37 !important;
            color: #E5C158 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title(t(lang, "🔐 Logowanie", "🔐 Log in"))
        st.markdown("---")

        if st.button(t(lang, "← Wróć", "← Back")):
            set_qp(page="landing", lang=lang)
            st.rerun()

        with st.form("login_form"):
            username = st.text_input(t(lang, "Nazwa użytkownika", "Username"))
            password = st.text_input(t(lang, "Hasło", "Password"), type="password")
            submit = st.form_submit_button(t(lang, "Zaloguj", "Log in"), use_container_width=True)

            if submit:
                if username and password:
                    success, user_data, msg = authenticate_user(username, password, lang=lang)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user = user_data
                        set_qp(page="dashboard", lang=lang)
                        st.rerun()
                    else:
                        st.error(msg)
                else:
                    st.error(t(lang, "Wypełnij wszystkie pola.", "Please fill in all fields."))

        st.markdown("---")
        if st.button(t(lang, "🔑 Zapomniałeś hasła?", "🔑 Forgot password?")):
            set_qp(page="forgot_password", lang=lang)
            st.rerun()

# ==============================================================================
# REGISTER PAGE
# ==============================================================================

elif page == "register":
    hide_sidebar_completely()
    
    # Register page styling with gold/yellow theme
    st.markdown("""
        <style>
        /* Register Page Background */
        .stApp {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f1419 100%);
        }
        
        /* Register Page Title */
        h1 {
            color: #D4AF37 !important;
            text-shadow: 0 0 15px rgba(212, 175, 55, 0.5);
            font-weight: 900;
        }
        
        /* Horizontal Rule */
        hr {
            border-color: rgba(212, 175, 55, 0.3);
            margin: 20px 0;
        }
        
        /* Form Container Styling */
        .stForm {
            background: rgba(14, 17, 23, 0.6);
            border: 2px solid rgba(212, 175, 55, 0.3);
            border-radius: 15px;
            padding: 30px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        
        /* Text Inputs */
        .stTextInput > div > div > input {
            background: rgba(14, 17, 23, 0.8) !important;
            border: 2px solid rgba(212, 175, 55, 0.3) !important;
            border-radius: 10px !important;
            color: #ffffff !important;
            padding: 12px 15px !important;
            transition: all 0.3s ease !important;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #D4AF37 !important;
            box-shadow: 0 0 15px rgba(212, 175, 55, 0.4) !important;
            outline: none !important;
        }
        
        .stTextInput > div > div > input::placeholder {
            color: rgba(255, 255, 255, 0.5) !important;
        }
        
        /* Input Labels */
        .stTextInput > label {
            color: #D4AF37 !important;
            font-weight: 700 !important;
            font-size: 16px !important;
            margin-bottom: 8px !important;
        }
        
        /* Buttons */
        .stButton > button {
            background: linear-gradient(135deg, #D4AF37 0%, #B8941F 100%) !important;
            color: #0b0b0b !important;
            border: 2px solid #D4AF37 !important;
            border-radius: 10px !important;
            font-weight: 800 !important;
            font-size: 18px !important;
            padding: 12px 24px !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(212, 175, 55, 0.3) !important;
            width: 100% !important;
        }
        
        .stButton > button:hover {
            background: linear-gradient(135deg, #E5C158 0%, #D4AF37 100%) !important;
            box-shadow: 0 6px 25px rgba(212, 175, 55, 0.5) !important;
            transform: translateY(-2px) !important;
        }
        
        /* Form Submit Button */
        button[type="submit"] {
            background: linear-gradient(135deg, #D4AF37 0%, #B8941F 100%) !important;
            color: #0b0b0b !important;
            border: 2px solid #D4AF37 !important;
            border-radius: 10px !important;
            font-weight: 800 !important;
            font-size: 18px !important;
            padding: 12px 24px !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(212, 175, 55, 0.3) !important;
        }
        
        button[type="submit"]:hover {
            background: linear-gradient(135deg, #E5C158 0%, #D4AF37 100%) !important;
            box-shadow: 0 6px 25px rgba(212, 175, 55, 0.5) !important;
            transform: translateY(-2px) !important;
        }
        
        /* Expander */
        .streamlit-expanderHeader {
            background: rgba(14, 17, 23, 0.6) !important;
            border: 1px solid rgba(212, 175, 55, 0.3) !important;
            border-radius: 8px !important;
            color: #D4AF37 !important;
        }
        
        /* Error/Success Messages */
        .stAlert {
            background: rgba(244, 67, 54, 0.1) !important;
            border-left: 4px solid #F44336 !important;
            border-radius: 8px !important;
        }
        
        .stSuccess {
            background: rgba(76, 175, 80, 0.1) !important;
            border-left: 4px solid #4CAF50 !important;
        }
        
        .stWarning {
            background: rgba(255, 193, 7, 0.1) !important;
            border-left: 4px solid #FFC107 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title(t(lang, "📝 Rejestracja", "📝 Register"))
        st.markdown("---")

        if st.button(t(lang, "← Wróć", "← Back")):
            set_qp(page="landing", lang=lang)
            st.rerun()

        with st.form("register_form"):
            new_username = st.text_input(t(lang, "Nazwa użytkownika", "Username"))
            new_email = st.text_input(t(lang, "Email", "Email"))

            with st.expander(t(lang, "ℹ️ Wymagania dotyczące hasła", "ℹ️ Password Requirements"), expanded=True):
                st.markdown(
                    t(lang,
                      """
                      **Hasło musi zawierać:**
                      - Co najmniej 8 znaków  
                      - Wielką literę  
                      - Małą literę  
                      - Cyfrę  
                      - Znak specjalny  
                      """,
                      """
                      **Password must include:**
                      - At least 8 characters  
                      - Uppercase letter  
                      - Lowercase letter  
                      - Digit  
                      - Special character  
                      """
                    )
                )

            new_password = st.text_input(t(lang, "Hasło", "Password"), type="password")
            confirm_password = st.text_input(t(lang, "Potwierdź hasło", "Confirm Password"), type="password")

            submit = st.form_submit_button(t(lang, "Utwórz konto", "Create account"), use_container_width=True)

            if submit:
                if not all([new_username, new_email, new_password, confirm_password]):
                    st.error(t(lang, "Wypełnij wszystkie pola.", "Please fill in all fields."))
                elif new_password != confirm_password:
                    st.error(t(lang, "Hasła nie pasują.", "Passwords do not match."))
                else:
                    success, msg = register_user_public(new_username, new_password, new_email)
                    if success:
                        st.success(t(lang, "Konto zostało utworzone pomyślnie", "Account created successfully"))
                        st.warning(
                            t(lang,
                              "⚠️ Zapisz swój Klucz Licencyjny teraz. Nie będzie pokazany ponownie.",
                              "⚠️ Save your License Key now. It will not be shown again."
                            )
                        )
                        st.code(msg)
                    else:
                        if isinstance(msg, list):
                            for error in msg:
                                st.error(error)
                        else:
                            st.error(msg)

# ==============================================================================
# FORGOT PASSWORD PAGE
# ==============================================================================

elif page == "forgot_password":
    hide_sidebar_completely()
    
    # Forgot password page styling with gold/yellow theme
    st.markdown("""
        <style>
        /* Forgot Password Page Background */
        .stApp {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f1419 100%);
        }
        
        /* Forgot Password Page Title */
        h1 {
            color: #D4AF37 !important;
            text-shadow: 0 0 15px rgba(212, 175, 55, 0.5);
            font-weight: 900;
        }
        
        /* Horizontal Rule */
        hr {
            border-color: rgba(212, 175, 55, 0.3);
            margin: 20px 0;
        }
        
        /* Form Container Styling */
        .stForm {
            background: rgba(14, 17, 23, 0.6);
            border: 2px solid rgba(212, 175, 55, 0.3);
            border-radius: 15px;
            padding: 30px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }
        
        /* Text Inputs */
        .stTextInput > div > div > input {
            background: rgba(14, 17, 23, 0.8) !important;
            border: 2px solid rgba(212, 175, 55, 0.3) !important;
            border-radius: 10px !important;
            color: #ffffff !important;
            padding: 12px 15px !important;
            transition: all 0.3s ease !important;
        }
        
        .stTextInput > div > div > input:focus {
            border-color: #D4AF37 !important;
            box-shadow: 0 0 15px rgba(212, 175, 55, 0.4) !important;
            outline: none !important;
        }
        
        /* Input Labels */
        .stTextInput > label {
            color: #D4AF37 !important;
            font-weight: 700 !important;
            font-size: 16px !important;
            margin-bottom: 8px !important;
        }
        
        /* Buttons */
        .stButton > button {
            background: linear-gradient(135deg, #D4AF37 0%, #B8941F 100%) !important;
            color: #0b0b0b !important;
            border: 2px solid #D4AF37 !important;
            border-radius: 10px !important;
            font-weight: 800 !important;
            font-size: 18px !important;
            padding: 12px 24px !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(212, 175, 55, 0.3) !important;
            width: 100% !important;
        }
        
        .stButton > button:hover {
            background: linear-gradient(135deg, #E5C158 0%, #D4AF37 100%) !important;
            box-shadow: 0 6px 25px rgba(212, 175, 55, 0.5) !important;
            transform: translateY(-2px) !important;
        }
        
        /* Form Submit Button */
        button[type="submit"] {
            background: linear-gradient(135deg, #D4AF37 0%, #B8941F 100%) !important;
            color: #0b0b0b !important;
            border: 2px solid #D4AF37 !important;
            border-radius: 10px !important;
            font-weight: 800 !important;
            font-size: 18px !important;
            padding: 12px 24px !important;
            transition: all 0.3s ease !important;
            box-shadow: 0 4px 15px rgba(212, 175, 55, 0.3) !important;
        }
        
        button[type="submit"]:hover {
            background: linear-gradient(135deg, #E5C158 0%, #D4AF37 100%) !important;
            box-shadow: 0 6px 25px rgba(212, 175, 55, 0.5) !important;
            transform: translateY(-2px) !important;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            background: rgba(14, 17, 23, 0.6);
            border-bottom: 2px solid rgba(212, 175, 55, 0.3);
        }
        
        .stTabs [data-baseweb="tab"] {
            color: rgba(255, 255, 255, 0.7) !important;
        }
        
        .stTabs [aria-selected="true"] {
            color: #D4AF37 !important;
            border-bottom: 3px solid #D4AF37;
        }
        
        /* Error/Success Messages */
        .stAlert {
            background: rgba(244, 67, 54, 0.1) !important;
            border-left: 4px solid #F44336 !important;
            border-radius: 8px !important;
        }
        
        .stSuccess {
            background: rgba(76, 175, 80, 0.1) !important;
            border-left: 4px solid #4CAF50 !important;
        }
        
        .stInfo {
            background: rgba(212, 175, 55, 0.1) !important;
            border-left: 4px solid #D4AF37 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title(t(lang, "🔑 Odzyskiwanie hasła", "🔑 Password Recovery"))
        st.markdown("---")

        if st.button(t(lang, "← Wróć do logowania", "← Back to login")):
            set_qp(page="login", lang=lang)
            st.rerun()

        tab1, tab2 = st.tabs([
            t(lang, "Resetuj hasło", "Reset Password"),
            t(lang, "Zapomniałem nazwy użytkownika", "Forgot Username")
        ])

        with tab1:
            with st.form("reset_password_form"):
                username = st.text_input(t(lang, "Nazwa użytkownika", "Username"))
                email = st.text_input(t(lang, "Email", "Email"))
                recovery = st.text_input(
                    t(lang, "Kod odzyskiwania lub Klucz licencyjny", "Recovery Code or License Key")
                )
                new_pw = st.text_input(t(lang, "Nowe hasło", "New Password"), type="password")
                confirm_pw = st.text_input(t(lang, "Potwierdź hasło", "Confirm Password"), type="password")

                submit = st.form_submit_button(t(lang, "Resetuj hasło", "Reset Password"), use_container_width=True)

                if submit:
                    if not all([username, email, recovery, new_pw, confirm_pw]):
                        st.error(t(lang, "Wypełnij wszystkie pola.", "Please fill in all fields."))
                    elif new_pw != confirm_pw:
                        st.error(t(lang, "Hasła nie pasują.", "Passwords do not match."))
                    else:
                        success, msg = reset_password_with_recovery(username, email, recovery, new_pw)
                        if success:
                            st.success(msg)
                            st.info(t(lang, "Możesz teraz się zalogować nowym hasłem.", "You can now login with your new password."))
                        else:
                            if isinstance(msg, list):
                                for error in msg:
                                    st.error(error)
                            else:
                                st.error(msg)

        with tab2:
            with st.form("forgot_username_form"):
                email = st.text_input(t(lang, "Email", "Email"))
                recovery = st.text_input(t(lang, "Kod odzyskiwania", "Recovery Code"))

                submit = st.form_submit_button(t(lang, "Odzyskaj nazwę użytkownika", "Recover Username"), use_container_width=True)

                if submit:
                    user = get_user_by_email(email)
                    if not user:
                        st.error(t(lang, "Użytkownik nie został znaleziony.", "User not found."))
                    else:
                        recovery_db = user[-1] if len(user) >= 10 else None
                        license_key = user[-3] if len(user) >= 8 else None
                        recovery_upper = recovery.upper().strip()
                        if recovery_upper in (
                            (recovery_db or "").upper(),
                            (license_key or "").upper(),
                        ):
                            st.success(t(lang, f"✅ Twoja nazwa użytkownika to: **{user[1]}**", f"✅ Your username is: **{user[1]}**"))
                        else:
                            st.error(t(lang, "Nieprawidłowy kod odzyskiwania.", "Invalid recovery code."))

# ==============================================================================
# AUTHENTICATED PAGES
# ==============================================================================

else:
    if not st.session_state.authenticated or not st.session_state.user:
        set_qp(page="login", lang=lang)
        st.rerun()
    
    user = st.session_state.user
    hide_default_streamlit_menu()
    
    # Global CSS styling with gold/yellow theme
    st.markdown("""
        <style>
        /* Global Gold/Yellow Theme */
        :root {
            --gold-primary: #D4AF37;
            --gold-light: rgba(212, 175, 55, 0.15);
            --gold-medium: rgba(212, 175, 55, 0.3);
            --gold-dark: #B8941F;
            --bg-dark: #0e1117;
            --bg-card: rgba(0, 0, 0, 0.4);
        }
        
        /* Main App Background */
        .stApp {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f1419 100%);
        }
        
        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, rgba(14, 17, 23, 0.95) 0%, rgba(10, 13, 18, 0.98) 100%);
            border-right: 2px solid var(--gold-medium);
        }
        
        [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] h3 {
            color: var(--gold-primary) !important;
            font-weight: 800;
            text-shadow: 0 0 10px rgba(212, 175, 55, 0.3);
        }
        
        /* Buttons - Custom Gold Theme with Premium Look */
        .stButton > button {
            background: linear-gradient(135deg, #D4AF37 0%, #B8941F 50%, #9A7A1A 100%) !important;
            color: #0b0b0b !important;
            border: none !important;
            border-radius: 25px !important;
            font-weight: 800 !important;
            font-size: 16px !important;
            padding: 14px 28px !important;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
            box-shadow: 0 8px 20px rgba(212, 175, 55, 0.4), 
                        0 4px 8px rgba(0, 0, 0, 0.3),
                        inset 0 1px 0 rgba(255, 255, 255, 0.2) !important;
            position: relative !important;
            overflow: hidden !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
            cursor: pointer !important;
        }
        
        .stButton > button::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
            transition: left 0.5s;
        }
        
        .stButton > button:hover::before {
            left: 100%;
        }
        
        .stButton > button:hover {
            background: linear-gradient(135deg, #E5C158 0%, #D4AF37 50%, #B8941F 100%) !important;
            box-shadow: 0 12px 30px rgba(212, 175, 55, 0.6), 
                        0 6px 12px rgba(0, 0, 0, 0.4),
                        inset 0 1px 0 rgba(255, 255, 255, 0.3) !important;
            transform: translateY(-3px) scale(1.02) !important;
        }
        
        .stButton > button:active {
            transform: translateY(-1px) scale(0.98) !important;
            box-shadow: 0 4px 12px rgba(212, 175, 55, 0.4), 
                        0 2px 4px rgba(0, 0, 0, 0.3) !important;
        }
        
        /* Secondary/Back buttons */
        .stButton > button[kind="secondary"],
        button[kind="secondary"] {
            background: rgba(14, 17, 23, 0.9) !important;
            color: #D4AF37 !important;
            border: 2px solid rgba(212, 175, 55, 0.5) !important;
            border-radius: 25px !important;
            box-shadow: 0 4px 15px rgba(212, 175, 55, 0.2), 
                        inset 0 1px 0 rgba(212, 175, 55, 0.1) !important;
        }
        
        .stButton > button[kind="secondary"]:hover,
        button[kind="secondary"]:hover {
            background: rgba(212, 175, 55, 0.15) !important;
            border-color: #D4AF37 !important;
            color: #E5C158 !important;
            box-shadow: 0 6px 20px rgba(212, 175, 55, 0.4), 
                        inset 0 1px 0 rgba(212, 175, 55, 0.2) !important;
            transform: translateY(-2px) !important;
        }
        
        /* Text Inputs */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {
            background: rgba(14, 17, 23, 0.8);
            border: 2px solid var(--gold-medium);
            border-radius: 8px;
            color: #ffffff;
            transition: all 0.3s ease;
        }
        
        .stTextInput > div > div > input:focus,
        .stTextArea > div > div > textarea:focus {
            border-color: var(--gold-primary);
            box-shadow: 0 0 10px rgba(212, 175, 55, 0.3);
        }
        
        /* Radio Buttons */
        .stRadio > div {
            background: rgba(14, 17, 23, 0.6);
            border-radius: 10px;
            padding: 10px;
        }
        
        .stRadio > div > label {
            color: #ffffff !important;
        }
        
        .stRadio > div > label > div:first-child {
            border-color: var(--gold-primary) !important;
        }
        
        .stRadio > div > label[data-baseweb="radio"] > div:first-child {
            border-color: var(--gold-primary) !important;
        }
        
        /* Checkboxes */
        .stCheckbox > label {
            color: #ffffff !important;
        }
        
        .stCheckbox > label > div:first-child {
            border-color: var(--gold-primary) !important;
        }
        
        /* File Uploader */
        .stFileUploader > div {
            background: rgba(14, 17, 23, 0.6);
            border: 2px dashed var(--gold-medium);
            border-radius: 10px;
        }
        
        /* Metrics */
        [data-testid="stMetricValue"] {
            color: var(--gold-primary) !important;
            font-weight: 800;
        }
        
        [data-testid="stMetricLabel"] {
            color: rgba(255, 255, 255, 0.8) !important;
        }
        
        /* Titles and Headers */
        h1, h2, h3 {
            color: var(--gold-primary) !important;
            text-shadow: 0 0 10px rgba(212, 175, 55, 0.3);
        }
        
        /* Info, Success, Warning, Error boxes */
        .stInfo {
            background: var(--gold-light);
            border-left: 4px solid var(--gold-primary);
        }
        
        .stSuccess {
            background: rgba(76, 175, 80, 0.1);
            border-left: 4px solid #4CAF50;
        }
        
        .stWarning {
            background: rgba(255, 193, 7, 0.1);
            border-left: 4px solid #FFC107;
        }
        
        .stError {
            background: rgba(244, 67, 54, 0.1);
            border-left: 4px solid #F44336;
        }
        
        /* Code blocks */
        .stCodeBlock {
            background: rgba(14, 17, 23, 0.9);
            border: 1px solid var(--gold-medium);
            border-radius: 8px;
        }
        
        /* Expander */
        .streamlit-expanderHeader {
            background: rgba(14, 17, 23, 0.6);
            border: 1px solid var(--gold-medium);
            border-radius: 8px;
            color: var(--gold-primary) !important;
        }
        
        /* Chat messages */
        [data-testid="stChatMessage"] {
            background: rgba(14, 17, 23, 0.6);
            border-left: 4px solid var(--gold-primary);
            border-radius: 8px;
            padding: 10px;
        }
        
        /* Selectbox */
        .stSelectbox > div > div {
            background: rgba(14, 17, 23, 0.8);
            border: 2px solid var(--gold-medium);
            border-radius: 8px;
        }
        
        /* Tabs */
        .stTabs [data-baseweb="tab-list"] {
            background: rgba(14, 17, 23, 0.6);
            border-bottom: 2px solid var(--gold-medium);
        }
        
        .stTabs [data-baseweb="tab"] {
            color: rgba(255, 255, 255, 0.7) !important;
        }
        
        .stTabs [aria-selected="true"] {
            color: var(--gold-primary) !important;
            border-bottom: 3px solid var(--gold-primary);
        }
        
        /* Dataframe */
        .stDataFrame {
            background: rgba(14, 17, 23, 0.6);
            border: 1px solid var(--gold-medium);
            border-radius: 8px;
        }
        
        /* Horizontal rule */
        hr {
            border-color: var(--gold-medium);
        }
        
        /* Markdown links */
        a {
            color: var(--gold-primary) !important;
        }
        
        a:hover {
            color: #E5C158 !important;
        }
        
        /* Spinner */
        .stSpinner > div {
            border-color: var(--gold-primary) transparent transparent transparent;
        }
        
        /* Conversation buttons - special style to ensure text is visible */
        button[key^="conv_"] {
            background: rgba(14, 17, 23, 0.8) !important;
            color: #D4AF37 !important;
            border: 2px solid rgba(212, 175, 55, 0.5) !important;
            text-transform: none !important;
            font-weight: 600 !important;
            text-align: left !important;
            padding-left: 15px !important;
        }
        
        button[key^="conv_"]:hover {
            background: rgba(212, 175, 55, 0.15) !important;
            border-color: #D4AF37 !important;
            color: #E5C158 !important;
        }
        
        button[key^="conv_"][disabled] {
            background: rgba(212, 175, 55, 0.2) !important;
            border-color: #D4AF37 !important;
            color: #D4AF37 !important;
            opacity: 1 !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    render_navigation_sidebar()
    
    # ==========================================================================
    # DASHBOARD
    # ==========================================================================
    
    if page == "dashboard":
        # Title and image side by side
        st.markdown("""
            <style>
            .image-wrapper-dashboard img {
                margin-top: -200px !important;
                position: relative !important;
                display: block !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        col_title, col_image = st.columns([2, 1])
        with col_title:
            st.markdown(f"""
            <h1 style="
                color: #FFD700;
                font-size: 3em;
                font-weight: 900;
                text-align: left;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8), 0 0 15px rgba(255, 215, 0, 0.6), 0 0 30px rgba(255, 215, 0, 0.4);
                letter-spacing: 4px;
                text-transform: uppercase;
                display: inline-block;
                border-bottom: 3px solid #FFD700;
                padding-bottom: 15px;
                margin-bottom: 20px;
            ">
                {t(lang, "STRONA GŁÓWNA", "DASHBOARD")}
            </h1>
            """, unsafe_allow_html=True)
        with col_image:
            st.markdown('<div class="image-wrapper-dashboard">', unsafe_allow_html=True)
            # Display image on the right side - enlarged
            import os
            if os.path.exists("0.jpeg"):
                st.image("0.jpeg", width=900, use_container_width=False)
            elif os.path.exists("0.jpg"):
                st.image("0.jpg", width=900, use_container_width=False)
            elif os.path.exists("0.png"):
                st.image("0.png", width=900, use_container_width=False)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        
        # Welcome message
        st.success(
            t(lang,
              f"Witaj, **{user['username']}** ({user['role']})",
              f"Welcome, **{user['username']}** ({user['role']})"
            )
        )
        
        st.markdown("---")
        
        # Application description
        st.markdown("""
        <style>
        .feature-card {
            background: linear-gradient(135deg, rgba(212, 175, 55, 0.15) 0%, rgba(255, 215, 0, 0.08) 100%);
            border: 2px solid rgba(212, 175, 55, 0.3);
            border-radius: 15px;
            padding: 20px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(212, 175, 55, 0.15);
        }
        .feature-card:hover {
            transform: translateY(-5px);
            border-color: rgba(255, 215, 0, 0.6);
            box-shadow: 0 8px 25px rgba(255, 215, 0, 0.3);
            background: linear-gradient(135deg, rgba(212, 175, 55, 0.25) 0%, rgba(255, 215, 0, 0.15) 100%);
        }
        </style>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="
            background: linear-gradient(135deg, rgba(212, 175, 55, 0.15) 0%, rgba(184, 148, 31, 0.1) 100%);
            border-left: 4px solid #D4AF37;
            border-radius: 10px;
            padding: 25px;
            margin: 20px 0;
        ">
            <h2 style="
                color: #FFD700;
                margin-bottom: 25px;
                font-size: 3em;
                font-weight: 900;
                text-align: center;
                text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8), 0 0 15px rgba(255, 215, 0, 0.6), 0 0 30px rgba(255, 215, 0, 0.4);
                letter-spacing: 4px;
                text-transform: uppercase;
                border-bottom: 3px solid #FFD700;
                padding-bottom: 15px;
            ">
                {t(lang, "📚 O APLIKACJI", "📚 ABOUT THE APPLICATION")}
            </h2>
            <div style="
                background: linear-gradient(135deg, rgba(212, 175, 55, 0.1) 0%, rgba(255, 215, 0, 0.05) 100%);
                border-left: 4px solid #D4AF37;
                padding: 20px;
                margin-bottom: 30px;
                border-radius: 10px;
                box-shadow: 0 4px 15px rgba(212, 175, 55, 0.2);
            ">
                <p style="
                    color: #ffffff; 
                    font-size: 17px; 
                    line-height: 1.9; 
                    margin: 0;
                    text-align: justify;
                    text-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
                ">
                    {t(lang, 
                    "Ta aplikacja to zaawansowane narzędzie AI do analizy, wyjaśniania i konwersji kodu programistycznego. " +
                    "Oferuje interaktywny chat z asystentem AI z wprowadzaniem głosowym, który może wyjaśnić działanie kodu, przeanalizować jego złożoność " +
                    "oraz zaproponować alternatywne implementacje. Aplikacja wspiera tłumaczenie kodu między różnymi językami programowania, " +
                    "analizę kodu ze zdjęć oraz generowanie wyjaśnień głosowych w sekcji analizy kodu.",
                    "This application is an advanced AI tool for analyzing, explaining, and converting programming code. " +
                    "It offers an interactive chat with an AI assistant with voice input that can explain how code works, analyze its complexity " +
                    "and propose alternative implementations. The application supports code translation between different programming languages, " +
                    "code analysis from images with voice explanations, and voice explanation generation."
                    )}
                </p>
            </div>
            <h3 style="
                color: #FFD700; 
                margin-top: 30px; 
                margin-bottom: 25px; 
                font-size: 1.8em;
                text-align: center;
                text-shadow: 0 0 15px rgba(255, 215, 0, 0.4);
                letter-spacing: 1px;
            ">
                {t(lang, "✨ Główne funkcje", "✨ Main Features")}
            </h3>
            <div style="
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 20px;
                margin-top: 20px;
            ">
                <div class="feature-card">
                    <div style="font-size: 2.5em; margin-bottom: 10px; text-align: center;">💬</div>
                    <h4 style="
                        color: #FFD700; 
                        margin: 0 0 12px 0;
                        font-size: 1.6em;
                        font-weight: 900;
                        text-align: center;
                        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8), 0 0 12px rgba(255, 215, 0, 0.6), 0 0 20px rgba(255, 215, 0, 0.4);
                        letter-spacing: 2px;
                        text-transform: uppercase;
                    ">
                        {t(lang, "Chat z AI", "AI Chat")}
                    </h4>
                    <p style="
                        color: #ffffff; 
                        font-size: 14px; 
                        line-height: 1.7; 
                        margin: 0;
                        text-align: center;
                    ">
                        {t(lang, 
                        "Interaktywne rozmowy z asystentem AI w różnych stylach (Sokrates, Dowódca, Trener, Artysta i więcej). Dostępne głosowe wprowadzanie wiadomości.",
                        "Interactive conversations with AI assistant in different styles (Socrates, Commander, Coach, Artist, and more). Voice input available.")}
                    </p>
                </div>
                <div class="feature-card">
                    <div style="font-size: 2.5em; margin-bottom: 10px; text-align: center;">📸</div>
                    <h4 style="
                        color: #FFD700; 
                        margin: 0 0 12px 0;
                        font-size: 1.6em;
                        font-weight: 900;
                        text-align: center;
                        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8), 0 0 12px rgba(255, 215, 0, 0.6), 0 0 20px rgba(255, 215, 0, 0.4);
                        letter-spacing: 2px;
                        text-transform: uppercase;
                    ">
                        {t(lang, "Analiza kodu", "Code Analysis")}
                    </h4>
                    <p style="
                        color: #ffffff; 
                        font-size: 14px; 
                        line-height: 1.7; 
                        margin: 0;
                        text-align: center;
                    ">
                        {t(lang, 
                        "Wklej kod jako tekst lub prześlij zdjęcie z kodem do szczegółowej analizy i wyjaśnienia. Dostępne wyjaśnienia głosowe.",
                        "Paste code as text or upload an image with code for detailed analysis and explanation. Voice explanations available.")}
                    </p>
                </div>
                <div class="feature-card">
                    <div style="font-size: 2.5em; margin-bottom: 10px; text-align: center;">🔄</div>
                    <h4 style="
                        color: #FFD700; 
                        margin: 0 0 12px 0;
                        font-size: 1.6em;
                        font-weight: 900;
                        text-align: center;
                        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8), 0 0 12px rgba(255, 215, 0, 0.6), 0 0 20px rgba(255, 215, 0, 0.4);
                        letter-spacing: 2px;
                        text-transform: uppercase;
                    ">
                        {t(lang, "Konwersja kodu", "Code Conversion")}
                    </h4>
                    <p style="
                        color: #ffffff; 
                        font-size: 14px; 
                        line-height: 1.7; 
                        margin: 0;
                        text-align: center;
                    ">
                        {t(lang, 
                        "Tłumaczenie kodu między różnymi językami programowania z wyjaśnieniami.",
                        "Translation of code between different programming languages with explanations.")}
                    </p>
                </div>
                <div class="feature-card">
                    <div style="font-size: 2.5em; margin-bottom: 10px; text-align: center;">📊</div>
                    <h4 style="
                        color: #FFD700; 
                        margin: 0 0 12px 0;
                        font-size: 1.6em;
                        font-weight: 900;
                        text-align: center;
                        text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.8), 0 0 12px rgba(255, 215, 0, 0.6), 0 0 20px rgba(255, 215, 0, 0.4);
                        letter-spacing: 2px;
                        text-transform: uppercase;
                    ">
                        {t(lang, "Śledzenie kosztów", "Cost Tracking")}
                    </h4>
                    <p style="
                        color: #ffffff; 
                        font-size: 14px; 
                        line-height: 1.7; 
                        margin: 0;
                        text-align: center;
                    ">
                        {t(lang, 
                        "Monitorowanie wydatków na użycie modeli AI z szczegółową historią.",
                        "Monitoring expenses for AI model usage with detailed history.")}
                    </p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ==========================================================================
    # CHAT WITH AI
    # ==========================================================================
    
    elif page == "chat":
        # Title and image side by side with vertical alignment
        st.markdown("""
            <style>
            .image-wrapper-chat img {
                margin-top: -200px !important;
                position: relative !important;
                display: block !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        col_title, col_image = st.columns([2, 1])
        with col_title:
            st.title(t(lang, "Chat z AI", "Chat with AI"))
        with col_image:
            st.markdown('<div class="image-wrapper-chat">', unsafe_allow_html=True)
            # Display image on the right side - same size as text_translate
            import os
            if os.path.exists("1.jpeg"):
                st.image("1.jpeg", width=700, use_container_width=False)
            elif os.path.exists("1.jpg"):
                st.image("1.jpg", width=700, use_container_width=False)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")

        # Get or create current conversation - simple logic like gpt_7_1
        if st.session_state.current_conversation_id is None:
            conversations = get_user_conversations(user['id'])
            if conversations:
                st.session_state.current_conversation_id = conversations[0]['id']
            else:
                # Create first conversation - find lowest available number
                base_name_pl = "Nowa konwersacja"
                base_name_en = "New Conversation"
                existing_numbers = []
                
                for conv in conversations:
                    conv_name = conv.get('name', '') or ''
                    if conv_name.startswith(base_name_pl + " "):
                        num_str = conv_name[len(base_name_pl + " "):].strip()
                        if num_str.isdigit():
                            existing_numbers.append(int(num_str))
                    elif conv_name.startswith(base_name_en + " "):
                        num_str = conv_name[len(base_name_en + " "):].strip()
                        if num_str.isdigit():
                            existing_numbers.append(int(num_str))
                
                # Find the lowest available number
                next_num = 1
                while next_num in existing_numbers:
                    next_num += 1
                
                conv_id = create_conversation(
                    user['id'],
                    t(lang, f"{base_name_pl} {next_num}", f"{base_name_en} {next_num}"),
                    DEFAULT_PERSONALITY,
                    model=DEFAULT_MODEL
                )
                st.session_state.current_conversation_id = conv_id

        conv_id = st.session_state.current_conversation_id
        conversation = get_conversation(conv_id)
        
        if not conversation:
            st.error(t(lang, "Błąd: Konwersacja nie została znaleziona.", "Error: Conversation not found."))
            st.stop()

        # Sidebar for conversation settings
        with st.sidebar:
            st.subheader(t(lang, "Ustawienia konwersacji", "Conversation Settings"))
            
            # Conversation name - use on_change callback like gpt_7_1
            def save_conversation_name():
                """Save conversation name when user presses Enter."""
                new_name = st.session_state.get("conv_name_input", "")
                if not new_name or new_name.strip() == "":
                    # Find lowest available number from existing conversation names
                    base_name_pl = "Nowa konwersacja"
                    base_name_en = "New Conversation"
                    all_conversations = get_user_conversations(user['id'])
                    existing_numbers = []
                    
                    for conv in all_conversations:
                        if conv['id'] == conv_id:
                            continue  # Skip current conversation
                        conv_name = conv.get('name', '') or ''
                        if conv_name.startswith(base_name_pl + " "):
                            num_str = conv_name[len(base_name_pl + " "):].strip()
                            if num_str.isdigit():
                                existing_numbers.append(int(num_str))
                        elif conv_name.startswith(base_name_en + " "):
                            num_str = conv_name[len(base_name_en + " "):].strip()
                            if num_str.isdigit():
                                existing_numbers.append(int(num_str))
                    
                    # Find the lowest available number
                    next_num = 1
                    while next_num in existing_numbers:
                        next_num += 1
                    
                    new_name = t(lang, f"{base_name_pl} {next_num}", f"{base_name_en} {next_num}")
                update_conversation(conv_id, name=new_name)
            
            conv_name_display = conversation.get('name', '') or t(lang, "Bez nazwy", "Unnamed")
            
            st.text_input(
                t(lang, "Nazwa konwersacji (Naciśnij Enter aby zastosować)", "Conversation Name (Press Enter to apply)"),
                value=conv_name_display,
                key="conv_name_input",
                on_change=save_conversation_name
            )
            
            # Personality selection
            personalities = list_personalities() + ["custom"]
            personality_names = {
                "default": t(lang, "Domyślna", "Default"),
                "socrates": t(lang, "Sokrates", "Socrates"),
                "commander": t(lang, "Dowódca", "Commander"),
                "coquette": t(lang, "Kokietka", "Coquette"),
                "artist": t(lang, "Artysta", "Artist"),
                "mischievous": t(lang, "Złośliwy", "Mischievous"),
                "coach": t(lang, "Trener", "Coach"),
                "grumpy": t(lang, "Zrzędliwy", "Grumpy"),
                "custom": t(lang, "Własna", "Custom")
            }
            
            current_personality = conversation.get('personality', DEFAULT_PERSONALITY)
            current_personality_name = "default"
            is_custom = True
            
            # Check if current personality matches any predefined one
            for pname in personalities:
                if pname == "custom":
                    continue
                ptext = get_personality(pname)
                if current_personality.strip() == ptext.strip():
                    current_personality_name = pname
                    is_custom = False
                    break
            
            # If no match found, it's a custom personality
            if is_custom:
                current_personality_name = "custom"
            
            selected_personality = st.selectbox(
                t(lang, "Osobowość AI", "AI Personality"),
                options=personalities,
                index=personalities.index(current_personality_name) if current_personality_name in personalities else 0,
                format_func=lambda x: personality_names.get(x, x)
            )
            
            # Custom personality text area
            if selected_personality == "custom":
                custom_personality_text = st.text_area(
                    t(lang, "Własna osobowość (Naciśnij Ctrl+Enter aby zastosować)", "Custom Personality (Press Ctrl+Enter to apply)"),
                    value=current_personality if is_custom else "",
                    height=150,
                    key="custom_personality_input",
                    help=t(lang, "Wpisz własną osobowość AI. Opisz jak ma się zachowywać asystent.", "Enter your custom AI personality. Describe how the assistant should behave.")
                )
                
                if st.button(t(lang, "Zastosuj własną osobowość", "Apply Custom Personality"), key="apply_custom_personality"):
                    if custom_personality_text.strip():
                        update_conversation(conv_id, personality=custom_personality_text.strip())
                        st.rerun()
                    else:
                        st.warning(t(lang, "Osobowość nie może być pusta!", "Personality cannot be empty!"))
            else:
                if selected_personality != current_personality_name:
                    update_conversation(conv_id, personality=get_personality(selected_personality))
                    st.rerun()
            
            st.markdown("---")
            
            # Model selection
            from app.services.ai_service import MODEL_PRICINGS, DEFAULT_MODEL
            current_model = conversation.get('model', DEFAULT_MODEL)
            
            # Model info for display
            model_info = {
                "gpt-4o-mini": {
                    "name": "GPT-4o Mini",
                    "description": t(lang, "Najtańszy • Szybki • Dobre dla prostych zadań", "Cheapest • Fast • Good for simple tasks"),
                    "cost_per_1k_tokens": t(lang, "~$0.75/1k tokenów", "~$0.75/1k tokens")
                },
                "gpt-4o": {
                    "name": "GPT-4o",
                    "description": t(lang, "Najlepszy • Najdroższy • Najwyższa jakość", "Best • Most Expensive • Highest Quality"),
                    "cost_per_1k_tokens": t(lang, "~$20/1k tokenów", "~$20/1k tokens")
                }
            }
            
            model_options = list(MODEL_PRICINGS.keys())
            model_index = model_options.index(current_model) if current_model in model_options else 0
            
            selected_model = st.selectbox(
                t(lang, "Model AI", "AI Model"),
                options=model_options,
                index=model_index,
                format_func=lambda x: f"{model_info[x]['name']} - {model_info[x]['description']}",
                help=t(lang, "Wybierz model AI. GPT-4o Mini jest tańszy, GPT-4o jest lepszy ale droższy.", "Choose AI model. GPT-4o Mini is cheaper, GPT-4o is better but more expensive.")
            )
            
            if selected_model != current_model:
                update_conversation(conv_id, model=selected_model)
                st.rerun()
            
            st.markdown("---")
            
            # Voice input - Real-time recording only
            st.markdown("""
            <style>
            .voice-input-container {
                background: transparent;
                border: none;
                border-radius: 0;
                padding: 0;
                margin: 20px 0;
                box-shadow: none;
            }
            .voice-input-title {
                color: #FFD700;
                font-size: 1.5em;
                font-weight: bold;
                margin: 0 0 20px 0;
                text-align: center;
            }
            .voice-input-instructions {
                color: #FFD700;
                text-align: center;
                font-size: 0.95em;
                margin-top: 15px;
                margin-bottom: 30px;
                opacity: 0.9;
            }
            .audio-player-container {
                margin: 20px 0;
                padding: 15px;
                background: rgba(255, 215, 0, 0.05);
                border-radius: 10px;
                border: 1px solid rgba(255, 215, 0, 0.3);
            }
            </style>
            """, unsafe_allow_html=True)
            
            st.markdown('<div class="voice-input-container">', unsafe_allow_html=True)
            # Title inside the container at the top
            st.markdown(f'<div class="voice-input-title">{t(lang, "Wprowadzanie głosowe", "Voice Input")}</div>', unsafe_allow_html=True)
            
            # Real-time audio recording - centered
            st.markdown('<div style="display: flex; justify-content: center; align-items: center; margin: 20px 0;">', unsafe_allow_html=True)
            audio_bytes = audio_recorder(
                text="",
                recording_color="#FFD700",
                neutral_color="#6c757d",
                icon_name="microphone",
                icon_size="3x",
                pause_threshold=2.0
            )
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown(f'<div class="voice-input-instructions">{t(lang, "Kliknij ikonę mikrofonu aby rozpocząć nagrywanie. Kliknij ponownie aby zakończyć.", "Click the microphone icon to start recording. Click again to stop.")}</div>', unsafe_allow_html=True)
            
            # Handle recorded audio
            if audio_bytes:
                st.audio(audio_bytes, format="audio/wav")
                
                # Convert audio_bytes to file-like object for transcription
                audio_file = io.BytesIO(audio_bytes)
                audio_file.name = "recording.wav"
                
                if st.button(t(lang, "Transkrybuj nagranie", "Transcribe recording"), use_container_width=True):
                    with st.spinner(t(lang, "Transkrypcja...", "Transcribing...")):
                        try:
                            transcribed_text = transcribe_audio(audio_file)
                            st.session_state.transcribed_text = transcribed_text
                            st.rerun()
                        except ValueError:
                            st.info(t(
                                lang,
                                "Aby skorzystać z transkrypcji, wprowadź swój klucz OpenAI API w panelu bocznym (sekcja „KLUCZ API”).",
                                "To use transcription, enter your OpenAI API key in the sidebar (\"API KEY\" section)."
                            ))
                        except Exception as e:
                            st.error(f"{t(lang, 'Błąd:', 'Error:')} {e}")
            
            # Display transcription if available
            if "transcribed_text" in st.session_state and st.session_state.transcribed_text:
                st.markdown('<div style="margin-top: 20px;">', unsafe_allow_html=True)
                transcribed_text = st.text_area(
                    t(lang, "Transkrypcja", "Transcription"),
                    value=st.session_state.transcribed_text,
                    key="transcribed_text_display",
                    height=100
                )
                st.markdown('</div>', unsafe_allow_html=True)
                
                # Button to send transcribed text to chat
                if st.button(t(lang, "Wyślij do czatu", "Send to chat"), use_container_width=True):
                    if transcribed_text:
                        # Add user message
                        add_message(conv_id, "user", transcribed_text)
                        # Clear transcription
                        st.session_state.transcribed_text = None
                        st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown("---")
            
            # Conversation list
            st.subheader(t(lang, "Konwersacje", "Conversations"))
            
            conversations = get_user_conversations(user['id'])
            
            # Show "New Conversation" button
            if st.button(t(lang, "➕ Nowa konwersacja", "➕ New Conversation")):
                # Find the lowest available number (not just max+1)
                # Extract all numbers from existing conversation names
                base_name_pl = "Nowa konwersacja"
                base_name_en = "New Conversation"
                existing_numbers = []
                
                for conv in conversations:
                    conv_name = conv.get('name', '') or ''
                    # Check if it matches numbered pattern
                    if conv_name.startswith(base_name_pl + " "):
                        num_str = conv_name[len(base_name_pl + " "):].strip()
                        if num_str.isdigit():
                            existing_numbers.append(int(num_str))
                    elif conv_name.startswith(base_name_en + " "):
                        num_str = conv_name[len(base_name_en + " "):].strip()
                        if num_str.isdigit():
                            existing_numbers.append(int(num_str))
                
                # Find the lowest available number
                next_num = 1
                while next_num in existing_numbers:
                    next_num += 1
                
                # Use the lowest available number in the name
                default_name = t(lang, f"{base_name_pl} {next_num}", f"{base_name_en} {next_num}")
                
                new_conv_id = create_conversation(
                    user['id'],
                    default_name,
                    get_personality(selected_personality),
                    model=DEFAULT_MODEL
                )
                st.session_state.current_conversation_id = new_conv_id
                st.rerun()
            
            # Display conversations with delete option
            if not conversations:
                st.info(t(lang, "Brak konwersacji. Kliknij 'Nowa konwersacja' aby utworzyć pierwszą.", "No conversations. Click 'New Conversation' to create the first one."))
            else:
                for conv in conversations[:10]:  # Show last 10
                    conv_name = conv.get('name', '') or ''
                    
                    # Ensure name is not empty - find lowest available number
                    if not conv_name or conv_name.strip() == "":
                        base_name_pl = "Nowa konwersacja"
                        base_name_en = "New Conversation"
                        existing_numbers = []
                        
                        for other_conv in conversations:
                            if other_conv['id'] == conv['id']:
                                continue  # Skip current conversation
                            other_name = other_conv.get('name', '') or ''
                            if other_name.startswith(base_name_pl + " "):
                                num_str = other_name[len(base_name_pl + " "):].strip()
                                if num_str.isdigit():
                                    existing_numbers.append(int(num_str))
                            elif other_name.startswith(base_name_en + " "):
                                num_str = other_name[len(base_name_en + " "):].strip()
                                if num_str.isdigit():
                                    existing_numbers.append(int(num_str))
                        
                        # Find the lowest available number
                        next_num = 1
                        while next_num in existing_numbers:
                            next_num += 1
                        
                        conv_name = t(lang, f"{base_name_pl} {next_num}", f"{base_name_en} {next_num}")
                        # Auto-save the name if it was empty
                        update_conversation(conv['id'], name=conv_name)
                    
                    # Display conversation with delete button
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        button_text = conv_name if len(conv_name) <= 50 else conv_name[:47] + "..."
                        if st.button(
                            button_text,
                            key=f"conv_{conv['id']}",
                            use_container_width=True,
                            disabled=conv['id'] == conv_id
                        ):
                            st.session_state.current_conversation_id = conv['id']
                            st.rerun()
                    
                    with col2:
                        if st.button("🗑️", key=f"delete_{conv['id']}", help=t(lang, "Usuń konwersację", "Delete conversation")):
                            if conv['id'] == conv_id:
                                # If deleting current conversation, switch to first other conversation
                                other_convs = [c for c in conversations if c['id'] != conv['id']]
                                if other_convs:
                                    st.session_state.current_conversation_id = other_convs[0]['id']
                                else:
                                    st.session_state.current_conversation_id = None
                            delete_conversation(conv['id'])
                            st.rerun()

        # Chat messages
        messages = get_conversation_messages(conv_id)
        
        # Display messages
        for msg in messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                if msg.get("usage"):
                    with st.expander(t(lang, "Szczegóły użycia", "Usage Details")):
                        st.json(msg["usage"])

        # Chat input
        prompt = st.chat_input(t(lang, "Napisz wiadomość...", "Type a message..."))
        
        # Handle transcribed text from voice input
        if "transcribed_text" in st.session_state and st.session_state.transcribed_text:
            prompt = st.session_state.transcribed_text
            del st.session_state.transcribed_text

        if prompt:
            # Add user message
            with st.chat_message("user"):
                st.markdown(prompt)
            
            add_message(conv_id, "user", prompt)
            
            # Get AI response
            with st.chat_message("assistant"):
                with st.spinner(t(lang, "Pisanie...", "Thinking...")):
                    # Prepare messages for API (last 20)
                    api_messages = [
                        {"role": msg["role"], "content": msg["content"]}
                        for msg in messages[-20:]
                    ]
                    api_messages.append({"role": "user", "content": prompt})
                    
                    # Get personality and model
                    personality_text = conversation.get('personality', DEFAULT_PERSONALITY)
                    # For custom personality, pass the text directly; for predefined, pass the name
                    if selected_personality == "custom":
                        personality_for_api = personality_text
                    else:
                        personality_for_api = selected_personality
                    selected_model = conversation.get('model', DEFAULT_MODEL)
                    
                    try:
                        response = chat_completion(
                            api_messages,
                            personality=personality_for_api,
                            model=selected_model,
                            conversation_history=messages
                        )
                    except ValueError:
                        st.info(t(
                            lang,
                            "Aby korzystać z czatu, wprowadź swój klucz OpenAI API w panelu bocznym (sekcja „KLUCZ API”).",
                            "To use chat, enter your OpenAI API key in the sidebar (\"API KEY\" section)."
                        ))
                    else:
                        st.markdown(response["content"])
                        
                        # Calculate and log cost with correct model
                        cost = calculate_cost(response["usage"], model=selected_model)
                        if cost > 0:  # Only log if cost is greater than 0
                            log_cost(user['id'], cost, conversation_id=conv_id)
                        
                        # Add assistant message
                        add_message(conv_id, "assistant", response["content"], response["usage"])
            
            st.rerun()

        # Show conversation cost
        conv_cost = get_conversation_cost(conv_id)
        st.sidebar.metric(
            t(lang, "Koszt konwersacji", "Conversation Cost"),
            f"${conv_cost:.6f}"
        )

    # ==========================================================================
    # IMAGE TRANSLATION
    # ==========================================================================
    
    elif page == "image_translate":
        # Title and image side by side with vertical alignment
        st.markdown("""
            <style>
            .image-wrapper-image-translate img {
                margin-top: -200px !important;
                position: relative !important;
                display: block !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        col_title, col_image = st.columns([2, 1])
        with col_title:
            st.title(t(lang, "Tłumaczenie i wyjaśnienie kodu", "Code Translation and Explanation"))
        with col_image:
            st.markdown('<div class="image-wrapper-image-translate">', unsafe_allow_html=True)
            # Display image on the right side - same size as other pages
            import os
            if os.path.exists("2.png"):
                st.image("2.png", width=700, use_container_width=False)
            elif os.path.exists("2.jpg"):
                st.image("2.jpg", width=700, use_container_width=False)
            elif os.path.exists("2.jpeg"):
                st.image("2.jpeg", width=700, use_container_width=False)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")

        # Input method selection
        input_method = st.radio(
            t(lang, "Wybierz metodę wprowadzania kodu", "Select code input method"),
            options=["paste_text", "upload"],
            format_func=lambda x: {
                "paste_text": t(lang, "📝 Wklej kod jako tekst", "📝 Paste code as text"),
                "upload": t(lang, "📁 Prześlij plik ze zdjęciem", "📁 Upload image file")
            }.get(x, x),
            horizontal=False
        )

        # Instructions
        if input_method == "paste_text":
            st.info(t(lang, 
                "💡 **Wskazówka:** Skopiuj kod tekstowy (Ctrl+C) i wklej tutaj (Ctrl+V).",
                "💡 **Tip:** Copy text code (Ctrl+C) and paste here (Ctrl+V)."
            ))

        col1, col2 = st.columns(2)
        with col1:
            translation_level = st.radio(
                t(lang, "Poziom wyjaśnienia", "Explanation Level"),
                options=["simple", "advanced"],
                format_func=lambda x: t(lang, "Ogólny" if x == "simple" else "Zaawansowany", 
                                      "General" if x == "simple" else "Advanced")
            )
        
        with col2:
            voice_option = st.selectbox(
                t(lang, "Wyjaśnienie głosowe", "Voice Explanation"),
                options=["none", "read", "narrate", "both"],
                format_func=lambda x: {
                    "none": t(lang, "Brak", "None"),
                    "read": t(lang, "Przeczytaj tekst", "Read Text"),
                    "narrate": t(lang, "Opowiedz w skrócie", "Narrate Briefly"),
                    "both": t(lang, "Oba", "Both")
                }.get(x, x)
            )
        
        # Model selection
        from app.services.ai_service import MODEL_PRICINGS, DEFAULT_MODEL
        model_info = {
            "gpt-4o-mini": {
                "name": "GPT-4o Mini",
                "description": t(lang, "Najtańszy • Szybki • Dobre dla prostych zadań", "Cheapest • Fast • Good for simple tasks")
            },
            "gpt-4o": {
                "name": "GPT-4o",
                "description": t(lang, "Najlepszy • Najdroższy • Najwyższa jakość", "Best • Most Expensive • Highest Quality")
            }
        }
        model_options = list(MODEL_PRICINGS.keys())
        selected_model = st.selectbox(
            t(lang, "Model AI", "AI Model"),
            options=model_options,
            index=0,
            format_func=lambda x: f"{model_info[x]['name']} - {model_info[x]['description']}",
            help=t(lang, "Wybierz model AI. GPT-4o Mini jest tańszy, GPT-4o jest lepszy ale droższy.", "Choose AI model. GPT-4o Mini is cheaper, GPT-4o is better but more expensive.")
        )

        code_text = None
        uploaded_file = None

        if input_method == "paste_text":
            # Add CSS to make the "Press Ctrl+Enter to apply" text more visible
            st.markdown("""
                <style>
                /* Make the Ctrl+Enter hint text larger and more visible with gold theme */
                div[data-testid="stTextArea"] label + div[style*="position: relative"] div[style*="position: absolute"] {
                    font-size: 14px !important;
                    font-weight: 600 !important;
                    color: #0b0b0b !important;
                    background: linear-gradient(135deg, #D4AF37 0%, #B8941F 100%) !important;
                    padding: 4px 8px !important;
                    border-radius: 4px !important;
                    box-shadow: 0 2px 6px rgba(212, 175, 55, 0.3) !important;
                }
                /* Alternative selector for Streamlit's hint text */
                div[data-testid="stTextArea"] > div > div > div[style*="position: absolute"] {
                    font-size: 14px !important;
                    font-weight: 600 !important;
                    color: #0b0b0b !important;
                    background: linear-gradient(135deg, #D4AF37 0%, #B8941F 100%) !important;
                }
                /* Target the hint text more specifically */
                .stTextArea > div > div > div[style*="absolute"] {
                    font-size: 16px !important;
                    font-weight: 700 !important;
                    color: #0b0b0b !important;
                    background: linear-gradient(135deg, #D4AF37 0%, #B8941F 100%) !important;
                    padding: 6px 10px !important;
                    border-radius: 6px !important;
                    box-shadow: 0 2px 8px rgba(212, 175, 55, 0.3) !important;
                }
                </style>
            """, unsafe_allow_html=True)
            
            # Direct code paste option
            code_text = st.text_area(
                label="",
                height=300,
                placeholder=t(lang, "Wklej swój kod tutaj używając Ctrl+V...", "Paste your code here using Ctrl+V..."),
                help=t(lang, "Skopiuj kod tekstowy i wklej tutaj. Jeśli masz obraz, użyj opcji 'Prześlij plik ze zdjęciem'.", 
                      "Copy text code and paste here. If you have an image, use 'Upload image file' option."),
                key="code_paste_textarea"
            )
            
            # Add visible hint below the text area (aligned to right)
            st.markdown(
                f'<div style="margin-top: -10px; margin-bottom: 10px; text-align: right;">'
                f'<span style="font-size: 16px; font-weight: 600; color: #0b0b0b; background: linear-gradient(135deg, #D4AF37 0%, #B8941F 100%); padding: 6px 12px; border-radius: 6px; display: inline-block; box-shadow: 0 2px 8px rgba(212, 175, 55, 0.3);">'
                f'💡 {t(lang, "Naciśnij Ctrl+Enter aby zastosować", "Press Ctrl+Enter to apply")}'
                f'</span></div>',
                unsafe_allow_html=True
            )
            
            if code_text and st.button(t(lang, "Wyjaśnij kod", "Explain Code"), use_container_width=True):
                with st.spinner(t(lang, "Przetwarzanie...", "Processing...")):
                    try:
                        # Use text translation to explain the code
                        if lang == "en":
                            if translation_level == "simple":
                                prompt = f"Explain briefly and generally what the following code does:\n\n```\n{code_text}\n```"
                            else:
                                prompt = f"""Analyze the following code in detail and provide:
1. Line-by-line explanation
2. Time and space complexity analysis (Big O notation)
3. Potential security issues and bugs
4. Optimization suggestions
5. Generate 2-3 alternative implementations of the same functionality
6. Compare all versions: pros/cons, performance, readability, maintainability
7. Design patterns used or that could be applied
8. Best practices and recommendations
9. Context and use cases where each version would be better

Format your response with clear sections. For alternative implementations, use code blocks with labels like "Alternative 1:", "Alternative 2:", etc.

Code to analyze:
```\n{code_text}\n```"""
                            
                            if voice_option in ["read", "both"]:
                                prompt += " Respond in a way suitable for reading aloud - use simple language and short sentences."
                        else:  # Polish
                            if translation_level == "simple":
                                prompt = f"Wyjaśnij krótko i ogólnie, co robi poniższy kod:\n\n```\n{code_text}\n```"
                            else:
                                prompt = f"""Przeanalizuj poniższy kod szczegółowo i przedstaw:
1. Wyjaśnienie linia po linii
2. Analizę złożoności czasowej i pamięciowej (notacja Big O)
3. Potencjalne problemy bezpieczeństwa i błędy
4. Sugestie optymalizacji
5. Wygeneruj minimum 2 alternatywne implementacje tej samej funkcjonalności (minimum 2, najlepiej 3)
6. Porównaj wszystkie wersje: zalety/wady, wydajność, czytelność, utrzymanie
7. Wzorce projektowe użyte lub które można zastosować
8. Najlepsze praktyki i rekomendacje
9. Kontekst i przypadki użycia, gdzie każda wersja byłaby lepsza

Sformatuj odpowiedź z wyraźnymi sekcjami. Dla alternatywnych implementacji użyj bloków kodu z etykietami jak "Alternatywa 1:", "Alternatywa 2:", "Alternatywa 3:", itd. Zawsze podaj minimum 2 alternatywy.

Kod do analizy:
```\n{code_text}\n```"""
                            
                            if voice_option in ["read", "both"]:
                                prompt += " Odpowiedz w sposób odpowiedni do odczytania na głos - użyj prostego języka i krótkich zdań."
                        
                        from app.services.ai_service import chat_completion
                        try:
                            response = chat_completion(
                                [{"role": "user", "content": prompt}],
                                personality="default",
                                model=selected_model
                            )
                        except ValueError:
                            st.info(t(
                                lang,
                                "Aby skorzystać z analizy kodu przez AI, wprowadź swój klucz OpenAI API w panelu bocznym (sekcja „KLUCZ API”).",
                                "To use AI code analysis, enter your OpenAI API key in the sidebar (\"API KEY\" section)."
                            ))
                            st.stop()
                        
                        # For advanced level, try to extract and display alternative code versions side by side
                        if translation_level == "advanced":
                            # Try to extract alternative code blocks from response
                            import re
                            content = response["content"]
                            
                            # Look for code blocks with "Alternative" or "Alternatywa" labels
                            alt_pattern = r'(?:Alternative|Alternatywa)\s*\d+[:]?\s*```(\w+)?\n(.*?)```'
                            alternatives = re.findall(alt_pattern, content, re.DOTALL)
                            
                            if alternatives:
                                st.subheader(t(lang, "Porównanie wersji kodu", "Code Versions Comparison"))
                                
                                # Display original code first
                                st.markdown(f"**{t(lang, 'Oryginalny kod', 'Original Code')}**")
                                st.code(code_text, language="python")
                                st.markdown("---")
                                
                                # Display at least 2 alternatives side by side (horizontal layout)
                                num_to_show = max(2, len(alternatives))
                                alternatives_to_show = alternatives[:num_to_show]
                                
                                # Force horizontal layout using HTML/CSS
                                st.markdown("""
                                    <style>
                                    .alternatives-container {
                                        display: flex !important;
                                        flex-direction: row !important;
                                        gap: 15px !important;
                                        width: 100% !important;
                                        overflow-x: auto !important;
                                    }
                                    .alternative-item {
                                        flex: 1 1 0% !important;
                                        min-width: 300px !important;
                                        max-width: 50% !important;
                                    }
                                    @media (max-width: 768px) {
                                        .alternatives-container {
                                            flex-direction: column !important;
                                        }
                                    }
                                    </style>
                                """, unsafe_allow_html=True)
                                
                                # Create HTML structure for alternatives
                                alternatives_html = '<div class="alternatives-container">'
                                
                                for idx, (lang_type, alt_code) in enumerate(alternatives_to_show):
                                    # Escape HTML in code
                                    import html
                                    escaped_code = html.escape(alt_code.strip())
                                    code_lang = lang_type.strip() if lang_type else "python"
                                    
                                    alternatives_html += f'''
                                    <div class="alternative-item">
                                        <h4 style="color: #D4AF37; margin-bottom: 10px;">{t(lang, f'Alternatywa {idx+1}', f'Alternative {idx+1}')}</h4>
                                        <pre style="background: #1e1e1e; padding: 15px; border-radius: 5px; overflow-x: auto; color: #d4d4d4; font-family: 'Courier New', monospace; white-space: pre-wrap; word-wrap: break-word;"><code class="language-{code_lang}">{escaped_code}</code></pre>
                                    </div>
                                    '''
                                
                                alternatives_html += '</div>'
                                st.markdown(alternatives_html, unsafe_allow_html=True)
                                
                                st.markdown("---")
                                st.subheader(t(lang, "Szczegółowa analiza", "Detailed Analysis"))
                            else:
                                st.subheader(t(lang, "Wyjaśnienie kodu", "Code Explanation"))
                            
                            st.markdown(content)
                        else:
                            st.subheader(t(lang, "Wyjaśnienie kodu", "Code Explanation"))
                            st.markdown(response["content"])
                        
                        # Calculate and log cost
                        cost = calculate_cost(response["usage"], model=selected_model)
                        log_cost(user['id'], cost)
                        
                        # Handle voice options
                        if voice_option in ["read", "both"]:
                            st.subheader(t(lang, "Wersja audio: Przeczytaj tekst", "Audio Version: Read Text"))
                            try:
                                # Truncate text to 4096 characters for TTS API
                                text_for_audio = response["content"][:4093] + "..." if len(response["content"]) > 4096 else response["content"]
                                audio_bytes = text_to_speech(text_for_audio)
                                st.audio(audio_bytes, format='audio/mp3')
                                if len(response["content"]) > 4096:
                                    st.warning(t(lang, 
                                        f"⚠️ Tekst został skrócony do 4096 znaków dla wersji audio (oryginał: {len(response['content'])} znaków).",
                                        f"⚠️ Text was truncated to 4096 characters for audio version (original: {len(response['content'])} characters)."
                                    ))
                            except ValueError:
                                st.info(t(
                                    lang,
                                    "Aby wygenerować dźwięk, wprowadź swój klucz OpenAI API w panelu bocznym (sekcja „KLUCZ API”).",
                                    "To generate audio, enter your OpenAI API key in the sidebar (\"API KEY\" section)."
                                ))
                            except Exception as e:
                                st.error(f"{t(lang, 'Błąd generowania audio:', 'Audio generation error:')} {e}")
                        
                        if voice_option in ["narrate", "both"]:
                            st.subheader(t(lang, "Wersja audio: Opowiedz w skrócie", "Audio Version: Narrate Briefly"))
                            try:
                                # Generate a brief narrative explanation
                                if lang == "en":
                                    narrate_prompt = f"""Tell me briefly what this code does, as if you're explaining it to someone in a conversation. Use simple language, short sentences, and avoid technical jargon. Focus on what the code does, not how it's implemented.

Code:
```\n{code_text}\n```"""
                                else:
                                    narrate_prompt = f"""Opowiedz w skrócie, co robi ten kod, jakbyś wyjaśniał komuś podczas rozmowy. Użyj prostego języka, krótkich zdań i unikaj technicznego żargonu. Skup się na tym, co kod robi, a nie jak jest zaimplementowany.

Kod:
```\n{code_text}\n```"""
                                
                                try:
                                    narrate_response = chat_completion(
                                        [{"role": "user", "content": narrate_prompt}],
                                        personality="default",
                                        model=selected_model
                                    )
                                except ValueError:
                                    st.info(t(
                                        lang,
                                        "Aby skorzystać z narracji audio, wprowadź swój klucz OpenAI API w panelu bocznym (sekcja „KLUCZ API”).",
                                        "To use audio narration, enter your OpenAI API key in the sidebar (\"API KEY\" section)."
                                    ))
                                    raise
                                
                                # Calculate and log cost for narration
                                narrate_cost = calculate_cost(narrate_response["usage"], model=selected_model)
                                log_cost(user['id'], narrate_cost)
                                
                                # Truncate text to 4096 characters for TTS API
                                narrate_text = narrate_response["content"][:4093] + "..." if len(narrate_response["content"]) > 4096 else narrate_response["content"]
                                try:
                                    narrate_audio = text_to_speech(narrate_text)
                                    st.audio(narrate_audio, format='audio/mp3')
                                except ValueError:
                                    st.info(t(
                                        lang,
                                        "Aby wygenerować narrację audio, wprowadź swój klucz OpenAI API w panelu bocznym (sekcja „KLUCZ API”).",
                                        "To generate audio narration, enter your OpenAI API key in the sidebar (\"API KEY\" section)."
                                    ))
                                
                                if len(narrate_response["content"]) > 4096:
                                    st.warning(t(lang, 
                                        f"⚠️ Tekst został skrócony do 4096 znaków dla wersji audio (oryginał: {len(narrate_response['content'])} znaków).",
                                        f"⚠️ Text was truncated to 4096 characters for audio version (original: {len(narrate_response['content'])} characters)."
                                    ))
                            except Exception as e:
                                st.error(f"{t(lang, 'Błąd generowania audio:', 'Audio generation error:')} {e}")
                        
                        st.success(t(lang, f"Koszt: ${cost:.4f}", f"Cost: ${cost:.4f}"))
                        
                    except Exception as e:
                        st.error(f"Błąd: {e}")
        
        else:
            # Image upload option
            uploaded_file = st.file_uploader(
                t(lang, "Prześlij zdjęcie z kodem", "Upload image with code"),
                type=['png', 'jpg', 'jpeg'],
                help=t(lang,
                    "Wybierz plik ze zdjęciem zawierającym kod do analizy.",
                    "Select a file with an image containing code to analyze."
                )
            )

            if uploaded_file:
                st.image(uploaded_file, caption=t(lang, "Przesłane zdjęcie", "Uploaded image"))
                
                if st.button(t(lang, "Konwertuj i wyjaśnij", "Convert and Explain"), use_container_width=True):
                    with st.spinner(t(lang, "Przetwarzanie...", "Processing...")):
                        try:
                            # Convert image to base64
                            image_bytes = uploaded_file.read()
                            image_b64 = base64.b64encode(image_bytes).decode('utf-8')
                            
                            # Get explanation
                            # Convert voice_option to use_voice boolean for backward compatibility
                            use_voice_bool = voice_option in ["read", "both"]
                            try:
                                result = explain_code_from_image(
                                    image_b64,
                                    level=translation_level,
                                    model=selected_model,
                                    use_voice=use_voice_bool,
                                    lang=lang
                                )
                            except ValueError:
                                st.info(t(
                                    lang,
                                    "Aby skorzystać z wyjaśniania kodu ze zdjęcia, wprowadź swój klucz OpenAI API w panelu bocznym (sekcja „KLUCZ API”).",
                                    "To use explaining code from image, enter your OpenAI API key in the sidebar (\"API KEY\" section)."
                                ))
                                st.stop()
                            
                            # For advanced level, try to extract and display alternative code versions side by side
                            if translation_level == "advanced":
                                # Try to extract alternative code blocks from response
                                import re
                                explanation = result["explanation"]
                                
                                # Look for code blocks with "Alternative" or "Alternatywa" labels
                                alt_pattern = r'(?:Alternative|Alternatywa)\s*\d+[:]?\s*```(\w+)?\n(.*?)```'
                                alternatives = re.findall(alt_pattern, explanation, re.DOTALL)
                                
                                if alternatives:
                                    st.subheader(t(lang, "Porównanie wersji kodu", "Code Versions Comparison"))
                                    
                                    # Always display in vertical layout: minimum 2 alternatives
                                    # Display at least 2 alternatives (or all if less than 2)
                                    num_to_show = max(2, len(alternatives))
                                    # Display at least 2 alternatives side by side (horizontal layout)
                                    alternatives_to_show = alternatives[:num_to_show]
                                    
                                    # Force horizontal layout using HTML/CSS
                                    st.markdown("""
                                        <style>
                                        .alternatives-container {
                                            display: flex !important;
                                            flex-direction: row !important;
                                            gap: 15px !important;
                                            width: 100% !important;
                                            overflow-x: auto !important;
                                        }
                                        .alternative-item {
                                            flex: 1 1 0% !important;
                                            min-width: 300px !important;
                                            max-width: 50% !important;
                                        }
                                        @media (max-width: 768px) {
                                            .alternatives-container {
                                                flex-direction: column !important;
                                            }
                                        }
                                        </style>
                                    """, unsafe_allow_html=True)
                                    
                                    # Create HTML structure for alternatives
                                    alternatives_html = '<div class="alternatives-container">'
                                    
                                    for idx, (lang_type, alt_code) in enumerate(alternatives_to_show):
                                        # Escape HTML in code
                                        import html
                                        escaped_code = html.escape(alt_code.strip())
                                        code_lang = lang_type.strip() if lang_type else "python"
                                        
                                        alternatives_html += f'''
                                        <div class="alternative-item">
                                            <h4 style="color: #D4AF37; margin-bottom: 10px;">{t(lang, f'Alternatywa {idx+1}', f'Alternative {idx+1}')}</h4>
                                            <pre style="background: #1e1e1e; padding: 15px; border-radius: 5px; overflow-x: auto; color: #d4d4d4; font-family: 'Courier New', monospace; white-space: pre-wrap; word-wrap: break-word;"><code class="language-{code_lang}">{escaped_code}</code></pre>
                                        </div>
                                        '''
                                    
                                    alternatives_html += '</div>'
                                    st.markdown(alternatives_html, unsafe_allow_html=True)
                                    
                                    st.markdown("---")
                                    st.subheader(t(lang, "Szczegółowa analiza", "Detailed Analysis"))
                                else:
                                    st.subheader(t(lang, "Wyjaśnienie kodu", "Code Explanation"))
                                
                                st.markdown(explanation)
                            else:
                                st.subheader(t(lang, "Wyjaśnienie kodu", "Code Explanation"))
                                st.markdown(result["explanation"])
                            
                            # Calculate and log cost
                            cost = calculate_cost(result["usage"], model=selected_model)
                            log_cost(user['id'], cost)
                            
                            # Handle voice options
                            if voice_option in ["read", "both"]:
                                st.subheader(t(lang, "Wersja audio: Przeczytaj tekst", "Audio Version: Read Text"))
                                try:
                                    # Truncate text to 4096 characters for TTS API
                                    text_for_audio = result["explanation"][:4093] + "..." if len(result["explanation"]) > 4096 else result["explanation"]
                                    audio_bytes = text_to_speech(text_for_audio)
                                    st.audio(audio_bytes, format='audio/mp3')
                                    if len(result["explanation"]) > 4096:
                                        st.warning(t(lang, 
                                            f"⚠️ Tekst został skrócony do 4096 znaków dla wersji audio (oryginał: {len(result['explanation'])} znaków).",
                                            f"⚠️ Text was truncated to 4096 characters for audio version (original: {len(result['explanation'])} characters)."
                                        ))
                                except ValueError:
                                    st.info(t(
                                        lang,
                                        "Aby wygenerować dźwięk, wprowadź swój klucz OpenAI API w panelu bocznym (sekcja „KLUCZ API”).",
                                        "To generate audio, enter your OpenAI API key in the sidebar (\"API KEY\" section)."
                                    ))
                                except Exception as e:
                                    st.error(f"{t(lang, 'Błąd generowania audio:', 'Audio generation error:')} {e}")
                            
                            if voice_option in ["narrate", "both"]:
                                st.subheader(t(lang, "Wersja audio: Opowiedz w skrócie", "Audio Version: Narrate Briefly"))
                                try:
                                    # Generate a brief narrative explanation
                                    # Note: We can't extract code from image easily, so we'll use the explanation as context
                                    if lang == "en":
                                        narrate_prompt = f"""Tell me briefly what this code does, as if you're explaining it to someone in a conversation. Use simple language, short sentences, and avoid technical jargon. Focus on what the code does, not how it's implemented.

Based on this explanation:
{result["explanation"][:1000]}"""
                                    else:
                                        narrate_prompt = f"""Opowiedz w skrócie, co robi ten kod, jakbyś wyjaśniał komuś podczas rozmowy. Użyj prostego języka, krótkich zdań i unikaj technicznego żargonu. Skup się na tym, co kod robi, a nie jak jest zaimplementowany.

Na podstawie tego wyjaśnienia:
{result["explanation"][:1000]}"""
                                    
                                    try:
                                        narrate_response = chat_completion(
                                            [{"role": "user", "content": narrate_prompt}],
                                            personality="default",
                                            model=selected_model
                                        )
                                    except ValueError:
                                        st.info(t(
                                            lang,
                                            "Aby skorzystać z narracji audio, wprowadź swój klucz OpenAI API w panelu bocznym (sekcja „KLUCZ API”).",
                                            "To use audio narration, enter your OpenAI API key in the sidebar (\"API KEY\" section)."
                                        ))
                                        raise
                                    
                                    # Calculate and log cost for narration
                                    narrate_cost = calculate_cost(narrate_response["usage"], model=selected_model)
                                    log_cost(user['id'], narrate_cost)
                                    
                                    # Truncate text to 4096 characters for TTS API
                                    narrate_text = narrate_response["content"][:4093] + "..." if len(narrate_response["content"]) > 4096 else narrate_response["content"]
                                    try:
                                        narrate_audio = text_to_speech(narrate_text)
                                        st.audio(narrate_audio, format='audio/mp3')
                                    except ValueError:
                                        st.info(t(
                                            lang,
                                            "Aby wygenerować narrację audio, wprowadź swój klucz OpenAI API w panelu bocznym (sekcja „KLUCZ API”).",
                                            "To generate audio narration, enter your OpenAI API key in the sidebar (\"API KEY\" section)."
                                        ))
                                    
                                    if len(narrate_response["content"]) > 4096:
                                        st.warning(t(lang, 
                                            f"⚠️ Tekst został skrócony do 4096 znaków dla wersji audio (oryginał: {len(narrate_response['content'])} znaków).",
                                            f"⚠️ Text was truncated to 4096 characters for audio version (original: {len(narrate_response['content'])} characters)."
                                        ))
                                except Exception as e:
                                    st.error(f"{t(lang, 'Błąd generowania audio:', 'Audio generation error:')} {e}")
                            
                            st.success(t(lang, f"Koszt: ${cost:.4f}", f"Cost: ${cost:.4f}"))
                            
                        except Exception as e:
                            st.error(f"Błąd: {e}")

    # ==========================================================================
    # TEXT TRANSLATION
    # ==========================================================================
    
    elif page == "text_translate":
        # Title and image side by side with vertical alignment
        st.markdown("""
            <style>
            .image-wrapper img {
                margin-top: -200px !important;
                position: relative !important;
                display: block !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        col_title, col_image = st.columns([2, 1])
        with col_title:
            st.title(t(lang, "Konwersja kodu między językami", "Code Conversion Between Languages"))
        with col_image:
            st.markdown('<div class="image-wrapper">', unsafe_allow_html=True)
            # Display image on the right side - larger size
            import os
            if os.path.exists("3.jpeg"):
                st.image("3.jpeg", width=700, use_container_width=False)
            elif os.path.exists("3.jpg"):
                st.image("3.jpg", width=700, use_container_width=False)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            source_language = st.text_input(
                t(lang, "Język źródłowy", "Source Language"),
                placeholder="np. Python, JavaScript, Java..."
            )
        with col2:
            target_language = st.text_input(
                t(lang, "Język docelowy", "Target Language"),
                placeholder="np. JavaScript, Python, C++..."
            )

        source_code = st.text_area(
            t(lang, "Kod źródłowy", "Source Code"),
            height=200,
            placeholder=t(lang, "Wklej tutaj kod do konwersji...", "Paste code here to convert...")
        )

        translation_level = st.radio(
            t(lang, "Poziom konwersji", "Conversion Level"),
            options=["simple", "advanced"],
            format_func=lambda x: t(lang, "Ogólny" if x == "simple" else "Zaawansowany", 
                                  "General" if x == "simple" else "Advanced"),
            horizontal=True
        )
        
        # Model selection
        from app.services.ai_service import MODEL_PRICINGS, DEFAULT_MODEL
        model_info = {
            "gpt-4o-mini": {
                "name": "GPT-4o Mini",
                "description": t(lang, "Najtańszy • Szybki • Dobre dla prostych zadań", "Cheapest • Fast • Good for simple tasks")
            },
            "gpt-4o": {
                "name": "GPT-4o",
                "description": t(lang, "Najlepszy • Najdroższy • Najwyższa jakość", "Best • Most Expensive • Highest Quality")
            }
        }
        model_options = list(MODEL_PRICINGS.keys())
        selected_model = st.selectbox(
            t(lang, "Model AI", "AI Model"),
            options=model_options,
            index=0,
            format_func=lambda x: f"{model_info[x]['name']} - {model_info[x]['description']}",
            help=t(lang, "Wybierz model AI. GPT-4o Mini jest tańszy, GPT-4o jest lepszy ale droższy.", "Choose AI model. GPT-4o Mini is cheaper, GPT-4o is better but more expensive.")
        )

        if st.button(t(lang, "Konwertuj kod", "Convert Code"), use_container_width=True):
            if not all([source_language, target_language, source_code]):
                st.error(t(lang, "Wypełnij wszystkie pola.", "Please fill in all fields."))
            else:
                with st.spinner(t(lang, "Konwersja...", "Converting...")):
                    try:
                        result = translate_code(
                            source_code,
                            source_language,
                            target_language,
                            level=translation_level,
                            model=selected_model,
                            lang=lang
                        )
                        
                        st.subheader(t(lang, "Skonwertowany kod", "Converted Code"))
                        st.code(result["translated_code"], language=target_language.lower())
                        
                        # Calculate and log cost
                        cost = calculate_cost(result["usage"], model=selected_model)
                        log_cost(user['id'], cost)
                        
                        st.success(t(lang, f"Koszt: ${cost:.4f}", f"Cost: ${cost:.4f}"))
                        
                    except Exception as e:
                        st.error(f"Błąd: {e}")

    # ==========================================================================
    # COSTS AND HISTORY
    # ==========================================================================
    
    elif page == "costs":
        # Title and image side by side with vertical alignment
        st.markdown("""
            <style>
            .image-wrapper-costs img {
                margin-top: -200px !important;
                position: relative !important;
                display: block !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        col_title, col_image = st.columns([2, 1])
        with col_title:
            st.title(t(lang, "Koszty i historia", "Costs and History"))
        with col_image:
            st.markdown('<div class="image-wrapper-costs">', unsafe_allow_html=True)
            # Display image on the right side - same size as other pages
            import os
            if os.path.exists("4.png"):
                st.image("4.png", width=700, use_container_width=False)
            elif os.path.exists("4.jpg"):
                st.image("4.jpg", width=700, use_container_width=False)
            elif os.path.exists("4.jpeg"):
                st.image("4.jpeg", width=700, use_container_width=False)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")

        # Total cost
        total = get_total_cost(user['id'])
        col1, col2 = st.columns(2)
        with col1:
            st.metric(t(lang, "Całkowity koszt (USD)", "Total Cost (USD)"), f"${total:.4f}")
        with col2:
            st.metric(t(lang, "Całkowity koszt (PLN)", "Total Cost (PLN)"), f"{total * 3.69:.2f}")

        st.markdown("---")
        
        # Daily costs
        st.subheader(t(lang, "Historia kosztów (ostatnie 60 dni)", "Cost History (Last 60 Days)"))
        daily_costs = get_daily_costs(user['id'], days=60)
        
        if daily_costs:
            import pandas as pd
            df = pd.DataFrame([
                {"Data": date, "Koszt (USD)": cost, "Koszt (PLN)": cost * 3.69}
                for date, cost in daily_costs.items()
            ])
            st.dataframe(df, use_container_width=True)
            
            # Chart
            st.line_chart(df.set_index("Data")["Koszt (USD)"])
        else:
            st.info(t(lang, "Brak danych o kosztach.", "No cost data available."))

    # ==========================================================================
    # ADMIN - USER MANAGEMENT
    # ==========================================================================
    
    elif page == "admin_users":
        from app.utils.auth import require_admin
        from app.data.users import (
            get_all_users, create_user_secure, delete_user,
            get_user_by_id, unlock_user_account, update_user
        )
        import pandas as pd
        
        admin_user = require_admin()
        
        # Title and image side by side with vertical alignment
        st.markdown("""
            <style>
            .image-wrapper-admin img {
                margin-top: -200px !important;
                position: relative !important;
                display: block !important;
            }
            </style>
        """, unsafe_allow_html=True)
        
        col_title, col_image = st.columns([2, 1])
        with col_title:
            st.title(t(lang, "Zarządzanie użytkownikami", "User Management"))
        with col_image:
            st.markdown('<div class="image-wrapper-admin">', unsafe_allow_html=True)
            # Display image on the right side - same size as other pages
            import os
            if os.path.exists("5.png"):
                st.image("5.png", width=700, use_container_width=False)
            elif os.path.exists("5.jpg"):
                st.image("5.jpg", width=700, use_container_width=False)
            elif os.path.exists("5.jpeg"):
                st.image("5.jpeg", width=700, use_container_width=False)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("---")
        st.caption(t(lang, f"Zalogowany jako: **{admin_user['username']}** ({admin_user['role']})", 
                    f"Logged in as: **{admin_user['username']}** ({admin_user['role']})"))
        
        # Flash messages
        if "flash_message" in st.session_state:
            if st.session_state.flash_type == "success":
                st.success(st.session_state.flash_message)
            else:
                st.error(st.session_state.flash_message)
            del st.session_state.flash_message
            del st.session_state.flash_type
        
        # Tabs
        tab_view, tab_add, tab_delete, tab_manage = st.tabs([
            t(lang, "Przegląd użytkowników", "View Users"),
            t(lang, "Dodaj użytkownika", "Add User"),
            t(lang, "Usuń użytkownika", "Delete User"),
            t(lang, "Zarządzaj kontami", "Manage Accounts")
        ])
        
        # TAB: VIEW USERS
        with tab_view:
            st.subheader(t(lang, "Wszyscy użytkownicy", "All Users"))
            
            if st.session_state.get("user_added", False):
                st.info(t(lang, "✅ Użytkownik został dodany pomyślnie! Tabela zaktualizowana.", 
                         "✅ User added successfully! Table updated."))
                st.session_state.user_added = False
            
            users = get_all_users()
            
            # Get first admin ID for protection indicator
            from app.data.users import get_first_admin_id
            first_admin_id = get_first_admin_id()
            
            if users:
                # Determine columns based on schema
                if len(users[0]) >= 10:
                    columns = [
                        "id", "username", "password_hash", "is_admin", "disabled",
                        "role", "email", "license_key", "failed_attempts", "recovery_code"
                    ]
                else:
                    columns = [
                        "id", "username", "password_hash", "is_admin", "disabled",
                        "role", "email", "license_key"
                    ]
                
                df = pd.DataFrame(users, columns=columns[:len(users[0])])
                
                # Add protection indicator for first admin
                if first_admin_id:
                    df["super_admin"] = df["id"].apply(
                        lambda x: "🛡️ " + t(lang, "Super Admin (Chroniony)", "Super Admin (Protected)") 
                        if x == first_admin_id else ""
                    )
                
                # Add status column
                if "disabled" in df.columns and "failed_attempts" in df.columns:
                    df["status"] = df.apply(
                        lambda row:
                            t(lang, "🔒 Zablokowane", "🔒 Locked")
                            if (row["disabled"] == 1 or (row["failed_attempts"] and row["failed_attempts"] >= 3))
                            else f"⚠️ {int(row['failed_attempts'])} {t(lang, 'prób', 'attempts')}"
                            if row["failed_attempts"] and row["failed_attempts"] > 0
                            else t(lang, "✅ Aktywne", "✅ Active"),
                        axis=1
                    )
                
                # Hide password_hash for display
                display_df = df.drop(columns=["password_hash"], errors="ignore")
                
                # Reorder columns to show super_admin first if it exists
                if "super_admin" in display_df.columns:
                    cols = ["super_admin"] + [col for col in display_df.columns if col != "super_admin"]
                    display_df = display_df[cols]
                
                st.dataframe(display_df, use_container_width=True)
                
                # Show info about first admin protection
                if first_admin_id:
                    st.info(t(lang, 
                        f"🛡️ **Uwaga:** Użytkownik z ID {first_admin_id} jest pierwszym administratorem (Super Admin) i jest chroniony przed usunięciem, wyłączeniem konta oraz utratą uprawnień administratora.",
                        f"🛡️ **Note:** User with ID {first_admin_id} is the first administrator (Super Admin) and is protected from deletion, account disabling, and loss of admin privileges."))
            else:
                st.info(t(lang, "Brak użytkowników w bazie danych.", "No users in database."))
        
        # TAB: ADD USER
        with tab_add:
            st.subheader(t(lang, "Dodaj nowego użytkownika", "Add New User"))
            
            with st.expander(t(lang, "ℹ️ Wymagania dotyczące hasła", "ℹ️ Password Requirements"), expanded=True):
                st.markdown(t(lang,
                    """
                    **Hasło musi spełniać wszystkie wymagania:**
                    - Co najmniej 8 znaków
                    - Jedna wielka litera
                    - Jedna mała litera
                    - Jedna cyfra
                    - Jeden znak specjalny
                    """,
                    """
                    **Password must meet all of the following requirements:**
                    - At least 8 characters
                    - One uppercase letter
                    - One lowercase letter
                    - One digit
                    - One special character
                    """
                ))
            
            username = st.text_input(t(lang, "Nazwa użytkownika", "Username"))
            password = st.text_input(t(lang, "Hasło", "Password"), type="password")
            email = st.text_input(t(lang, "Email", "Email"))
            role = st.selectbox(t(lang, "Rola", "Role"), ["user", "admin"])
            
            if st.button(t(lang, "Utwórz użytkownika", "Create User")):
                if not username or not password:
                    st.error(t(lang, "Nazwa użytkownika i hasło są wymagane.", "Username and password are required."))
                else:
                    is_admin = 1 if role == "admin" else 0
                    success, message = create_user_secure(
                        username, password, is_admin, 0, role, email
                    )
                    
                    if success:
                        st.session_state.user_added = True
                        st.session_state.flash_message = t(lang, "Użytkownik utworzony pomyślnie.", "User created successfully.")
                        st.session_state.flash_type = "success"
                        st.rerun()
                    else:
                        if isinstance(message, list):
                            for err in message:
                                st.error(err)
                        else:
                            st.error(message)
        
        # TAB: DELETE USER
        with tab_delete:
            st.subheader(t(lang, "Usuń użytkownika po ID", "Delete User by ID"))
            
            user_id = st.number_input(t(lang, "ID użytkownika", "User ID"), min_value=1, step=1)
            
            if st.button(t(lang, "Usuń", "Delete")):
                user_row = get_user_by_id(int(user_id))
                
                if not user_row:
                    st.error(t(lang, "Użytkownik nie został znaleziony.", "User not found."))
                else:
                    success, message = delete_user(int(user_id))
                    st.session_state.flash_message = message
                    st.session_state.flash_type = "success" if success else "error"
                    st.rerun()
        
        # TAB: MANAGE ACCOUNTS
        with tab_manage:
            st.subheader(t(lang, "🔧 Zarządzanie kontami", "🔧 Account Management"))
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"### {t(lang, '🔓 Odblokuj konto', '🔓 Unlock Account')}")
                unlock_id = st.number_input(
                    t(lang, "ID użytkownika do odblokowania", "User ID to Unlock"),
                    min_value=1, step=1, key="unlock_id"
                )
                
                if st.button(t(lang, "Odblokuj użytkownika", "Unlock User")):
                    success, message = unlock_user_account(int(unlock_id))
                    st.session_state.flash_message = message
                    st.session_state.flash_type = "success" if success else "error"
                    st.rerun()
            
            with col2:
                st.markdown(f"### {t(lang, '🔑 Resetuj hasło użytkownika', '🔑 Reset User Password')}")
                reset_id = st.number_input(
                    t(lang, "ID użytkownika", "User ID"), 
                    min_value=1, step=1, key="reset_id"
                )
                new_pw = st.text_input(t(lang, "Nowe hasło", "New Password"), type="password")
                confirm_pw = st.text_input(t(lang, "Potwierdź hasło", "Confirm Password"), type="password")
                
                if st.button(t(lang, "Resetuj hasło", "Reset Password")):
                    if new_pw != confirm_pw:
                        st.error(t(lang, "Hasła nie pasują.", "Passwords do not match."))
                    else:
                        user_row = get_user_by_id(int(reset_id))
                        
                        if not user_row:
                            st.error(t(lang, "Użytkownik nie został znaleziony.", "User not found."))
                        else:
                            if len(user_row) >= 8:
                                user_id, username, _, is_admin, _, role, email, license_key = user_row[:8]
                            else:
                                user_id, username, _, is_admin, _, role, email = user_row[:7]
                                license_key = None
                            
                            success, message = update_user(
                                user_id, username, password=new_pw,
                                is_admin=is_admin, disabled=0, role=role,
                                email=email, license_key=license_key
                            )
                            
                            st.session_state.flash_message = message
                            st.session_state.flash_type = "success" if success else "error"
                            st.rerun()

    else:
        st.error(t(lang, "Strona nie została znaleziona.", "Page not found."))
        if st.button(t(lang, "Wróć do strony głównej", "Back to Dashboard")):
            set_qp(page="dashboard", lang=lang)
            st.rerun()
