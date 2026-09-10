"""KisanSense — Main application entry point.

Handles page configuration, global styling, session-state initialization,
and navigation between pages while preserving top navbar control.
"""

import streamlit as st

from components.navbar import render_navbar
from services.farm_service import init_farm_profile
from utils.config import APP_NAME, PAGE_ICON
from utils.seo import get_page_title, inject_seo_head
from utils.translations import DEFAULT_LANG
from views import alerts, analytics, assistance, devices, farm, home, irrigation, not_found, vision, weather

PAGES = {
    "home": home,
    "farm": farm,
    "weather": weather,
    "irrigation": irrigation,
    "vision": vision,
    "assistant": assistance,
    "alerts": alerts,
    "devices": devices,
    "analytics": analytics,
}



def load_css(path: str) -> None:
    """Inject the app's design system and active theme overrides."""
    try:
        with open(path, "r", encoding="utf-8") as css_file:
            st.markdown(f"<style>{css_file.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

    if st.session_state.get("theme", "light") == "dark":
        dark_css = """
        <style>
        :root, body, .stApp {
          --color-bg: #0B1412 !important;
          --color-surface: #132522 !important;
          --color-surface-alt: #162A27 !important;
          --color-border: #23433D !important;
          --color-text: #F2F7F5 !important;
          --color-text-muted: #A9BFBA !important;

          --color-primary: #1F8F70 !important;
          --color-primary-soft: #1A302C !important;
          --color-accent: #25C997 !important;

          --color-good: #25C997 !important;
          --color-good-soft: #18312C !important;
          --color-warning: #E5A43B !important;
          --color-warning-soft: #382A14 !important;
          --color-alert: #E5684A !important;
          --color-alert-soft: #3D1F17 !important;

          --shadow-card: 0 2px 8px rgba(0, 0, 0, 0.4), 0 12px 24px rgba(0, 0, 0, 0.5) !important;
          background-color: #0B1412 !important;
          color: #F2F7F5 !important;
        }

        .stApp {
          background-color: #0B1412 !important;
          color: #F2F7F5 !important;
        }

        /* Streamlit native widget styling in dark mode */
        [data-baseweb="input"], [data-baseweb="base-input"] {
          background-color: #132522 !important;
          border-color: #23433D !important;
          color: #F2F7F5 !important;
        }
        [data-baseweb="input"] input, [data-baseweb="base-input"] input, textarea {
          color: #F2F7F5 !important;
          background-color: transparent !important;
        }
        [data-baseweb="select"] > div {
          background-color: #132522 !important;
          border-color: #23433D !important;
          color: #F2F7F5 !important;
        }
        [data-baseweb="select"] span {
          color: #F2F7F5 !important;
        }
        [data-baseweb="popover"], [data-baseweb="menu"], [data-baseweb="menu"] ul {
          background-color: #132522 !important;
          color: #F2F7F5 !important;
          border-color: #23433D !important;
        }
        [data-baseweb="menu"] li {
          color: #F2F7F5 !important;
        }
        [data-baseweb="menu"] li:hover, [data-baseweb="menu"] li[aria-selected="true"] {
          background-color: #1A302C !important;
        }
        [data-testid="stExpander"] {
          background-color: #132522 !important;
          border-color: #23433D !important;
        }
        [data-testid="stExpander"] summary {
          color: #F2F7F5 !important;
        }
        [data-testid="stExpander"] summary:hover {
          color: #25C997 !important;
        }
        .stButton > button {
          background-color: #132522 !important;
          border-color: #23433D !important;
          color: #F2F7F5 !important;
        }
        .stButton > button:hover {
          background-color: #1A302C !important;
          color: #25C997 !important;
          border-color: #25C997 !important;
        }
        .stButton > button:disabled {
          background-color: #1A302C !important;
          color: #25C997 !important;
          border-color: #1F8F70 !important;
          font-weight: 600 !important;
        }

        /* --------------------------------------------------------------------------
           KISANSENSE ASSISTANT (Native Charcoal-Green Dashboard Panel)
           -------------------------------------------------------------------------- */

        /* Assistant Panel Container */
        .assistant-dashboard-panel,
        .st-key-home_assistant_panel {
          background-color: #132522 !important;
          border: 1px solid #23433D !important;
          border-radius: 12px !important;
          padding: 1.25rem 1.25rem 1rem 1.25rem !important;
          margin-top: 1rem !important;
          margin-bottom: 1.5rem !important;
          box-shadow: none !important;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-home_assistant_panel),
        [data-testid="stVerticalBlockBorderWrapper"]:has(.assistant-dashboard-panel) {
          background-color: #132522 !important;
          border: 1px solid #23433D !important;
          border-radius: 12px !important;
          box-shadow: none !important;
        }

        /* Assistant Header */
        .assistant-panel-header {
          display: flex !important;
          align-items: center !important;
          gap: 0.75rem !important;
          margin-bottom: 0.85rem !important;
        }
        .assistant-header-icon {
          width: 36px !important;
          height: 36px !important;
          min-width: 36px !important;
          border-radius: 50% !important;
          background-color: #162A27 !important;
          border: 1px solid #23433D !important;
          display: flex !important;
          align-items: center !important;
          justify-content: center !important;
          font-size: 1.15rem !important;
          flex-shrink: 0 !important;
        }
        .assistant-title {
          font-family: var(--font-sans) !important;
          font-size: 1.15rem !important;
          font-weight: 700 !important;
          color: #F2F7F5 !important;
          margin: 0 !important;
          line-height: 1.2 !important;
        }
        .assistant-subtitle {
          font-size: 0.88rem !important;
          color: #A9BFBA !important;
          margin: 0.2rem 0 0 0 !important;
          line-height: 1.4 !important;
        }

        /* Prompt Chips: compact, subtle border, light text, dark-green hover */
        div[class*="st-key-chip_home_"] button,
        div[class*="st-key-chip_asst_"] button {
          background-color: #162A27 !important;
          border: 1px solid #2A5149 !important;
          color: #F2F7F5 !important;
          font-size: 0.82rem !important;
          font-weight: 500 !important;
          padding: 0.35rem 0.65rem !important;
          border-radius: 6px !important;
          min-height: 32px !important;
          height: 32px !important;
          white-space: nowrap !important;
          text-overflow: ellipsis !important;
          overflow: hidden !important;
          transition: all 0.15s ease !important;
          box-shadow: none !important;
        }
        div[class*="st-key-chip_home_"] button:hover,
        div[class*="st-key-chip_asst_"] button:hover {
          background-color: #1F8F70 !important;
          border-color: #25C997 !important;
          color: #FFFFFF !important;
        }

        /* Chat Messages */
        [data-testid="stChatMessage"] {
          background-color: #18312C !important;
          border: 1px solid #23433D !important;
          border-radius: 10px !important;
          color: #F2F7F5 !important;
          padding: 0.75rem 1rem !important;
          margin-bottom: 0.65rem !important;
          box-shadow: none !important;
        }
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]),
        [data-testid="stChatMessage"][data-role="user"] {
          background-color: #1A302C !important;
          border-color: #2A5149 !important;
          color: #F2F7F5 !important;
        }
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]),
        [data-testid="stChatMessage"][data-role="assistant"] {
          background-color: #18312C !important;
          border-color: #23433D !important;
          border-left: 3px solid #1F8F70 !important;
          color: #F2F7F5 !important;
        }
        [data-testid="stChatMessage"] p,
        [data-testid="stChatMessage"] div,
        [data-testid="stChatMessage"] span {
          color: #F2F7F5 !important;
        }
        [data-testid="stChatMessage"] [data-testid="stChatMessageAvatarCustom"],
        [data-testid="stChatMessage"] [data-testid="chatAvatarIcon-assistant"],
        [data-testid="stChatMessage"] [data-testid="chatAvatarIcon-user"] {
          background-color: #162A27 !important;
          border: 1px solid #23433D !important;
        }

        /* Chat Input Bar: compact, dark charcoal-green background, subtle border */
        [data-testid="stChatInput"] {
          background-color: #10201D !important;
          border: 1px solid #2A5149 !important;
          border-radius: 10px !important;
          box-shadow: none !important;
          padding: 3px 6px !important;
        }
        [data-testid="stChatInput"]:focus-within {
          border-color: #25C997 !important;
          box-shadow: 0 0 0 1px #25C997 !important;
        }
        [data-testid="stChatInput"] > div {
          background-color: transparent !important;
        }
        [data-testid="stChatInput"] textarea {
          color: #F2F7F5 !important;
          font-family: var(--font-sans) !important;
          font-size: 0.9rem !important;
          background-color: transparent !important;
          min-height: 38px !important;
        }
        [data-testid="stChatInput"] textarea::placeholder {
          color: #A9BFBA !important;
        }
        [data-testid="stChatInput"] button,
        [data-testid="stChatInputSubmitButton"] {
          background-color: #1F8F70 !important;
          color: #F2F7F5 !important;
          border-radius: 50% !important;
          border: none !important;
          width: 32px !important;
          height: 32px !important;
          min-height: 32px !important;
          max-height: 32px !important;
          display: inline-flex !important;
          align-items: center !important;
          justify-content: center !important;
          transition: background-color 0.2s ease !important;
          margin: auto 0 !important;
        }
        [data-testid="stChatInput"] button:hover,
        [data-testid="stChatInputSubmitButton"]:hover {
          background-color: #25C997 !important;
          color: #0B1412 !important;
        }
        [data-testid="stChatInput"] button:disabled,
        [data-testid="stChatInputSubmitButton"]:disabled {
          background-color: #1A302C !important;
          color: #5E7A73 !important;
        }
        [data-testid="stChatInputInstructions"] {
          color: #5E7A73 !important;
          font-size: 0.72rem !important;
        }

        /* Prevent any white or light floating dock bar */
        [data-testid="stBottom"],
        [data-testid="stBottom"] > div,
        [data-testid="stBottomBlockContainer"],
        .stBottom {
          background: transparent !important;
          background-color: transparent !important;
          box-shadow: none !important;
        }

        /* --------------------------------------------------------------------------
           DASHBOARD HEROES & CARDS (Dark Theme Cohesion)
           -------------------------------------------------------------------------- */
        .farm-health-hero-good {
          background: linear-gradient(135deg, #132522 88%, #162A27 100%) !important;
        }
        .farm-health-hero-warning {
          background: linear-gradient(135deg, #132522 88%, #2d2010 100%) !important;
        }
        .farm-health-hero-alert {
          background: linear-gradient(135deg, #132522 88%, #2d1812 100%) !important;
        }
        .farm-health-hero-critical {
          background: linear-gradient(135deg, #132522 88%, #361414 100%) !important;
        }
        .metric-card {
          background-color: #132522 !important;
          border-color: #23433D !important;
        }
        .insight-card {
          background-color: #132522 !important;
          border-color: #23433D !important;
        }
        .action-hero-card {
          background-color: #132522 !important;
          border-color: #23433D !important;
        }
        .action-secondary-box {
          background-color: #162A27 !important;
          border-color: #23433D !important;
          color: #F2F7F5 !important;
        }
        .vision-card, .vision-guidance-item {
          background-color: #132522 !important;
          border-color: #23433D !important;
          color: #F2F7F5 !important;
        }
        .vision-section-box {
          background-color: #162A27 !important;
          border-color: #23433D !important;
          color: #F2F7F5 !important;
        }
        .vision-result-healthy {
          background: linear-gradient(135deg, #132522 88%, #162A27 100%) !important;
        }
        .vision-result-warning {
          background: linear-gradient(135deg, #132522 88%, #2d2010 100%) !important;
        }
        .vision-result-rejected {
          background: linear-gradient(135deg, #132522 88%, #2d1812 100%) !important;
        }
        .weather-context-banner, .weather-metric-card, .weather-impact-card, .forecast-card, .weather-no-risks-card, .weather-assistant-box {
          background-color: #132522 !important;
          border-color: #23433D !important;
          color: #F2F7F5 !important;
        }
        .weather-action-hero {
          background-color: #132522 !important;
        }
        .weather-action-good {
          background: linear-gradient(135deg, #132522 88%, #162A27 100%) !important;
          border-color: #25C997 !important;
        }
        .weather-action-warning {
          background: linear-gradient(135deg, #132522 88%, #2d2010 100%) !important;
          border-color: #E5A43B !important;
        }
        .weather-action-alert {
          background: linear-gradient(135deg, #132522 88%, #2d1812 100%) !important;
          border-color: #E5684A !important;
        }
        .weather-risk-banner {
          background-color: #132522 !important;
        }
        .home-weather-banner {
          background-color: #132522 !important;
          border-color: #23433D !important;
          color: #F2F7F5 !important;
        }
        </style>
        """
        st.markdown(dark_css, unsafe_allow_html=True)


def init_session_state() -> None:
    # Safely inspect query parameters on initial load
    try:
        query_page = st.query_params.get("page")
    except Exception:
        query_page = None

    if "page" not in st.session_state:
        if query_page and (query_page in PAGES or query_page == "404"):
            st.session_state.page = query_page
        elif query_page:
            st.session_state.page = "404"
        else:
            st.session_state.page = "home"

    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "lang" not in st.session_state:
        st.session_state.lang = DEFAULT_LANG
    if "sim_condition" not in st.session_state:
        st.session_state.sim_condition = "NORMAL"
    if "theme" not in st.session_state:
        st.session_state.theme = "light"
    if "latest_vision_result" not in st.session_state:
        st.session_state.latest_vision_result = None
    if "latest_weather_snapshot" not in st.session_state:
        st.session_state.latest_weather_snapshot = None
    init_farm_profile()


def main() -> None:
    init_session_state()
    current_page = st.session_state.get("page", "home")

    # Sync query parameter with current active page
    try:
        if st.query_params.get("page") != current_page:
            st.query_params["page"] = current_page
    except Exception:
        pass

    page_title = get_page_title(current_page)

    st.set_page_config(
        page_title=page_title,
        page_icon=PAGE_ICON,
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    load_css("assets/style.css")
    inject_seo_head(current_page)

    render_navbar(current_page=current_page)

    if current_page in PAGES:
        page_module = PAGES[current_page]
    else:
        page_module = not_found
    page_module.render()


if __name__ == "__main__":
    main()
