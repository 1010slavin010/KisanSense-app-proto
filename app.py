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
          --color-bg: #0F1916 !important;
          --color-surface: #162723 !important;
          --color-surface-alt: #1E352F !important;
          --color-surface-muted: #25413A !important;
          --color-surface-elevated: #28473F !important;

          --color-border: #2D4E45 !important;
          --color-border-subtle: #223C35 !important;
          --color-border-focus: #34D399 !important;

          --color-text: #F8FAFC !important;
          --color-text-secondary: #CBD5E1 !important;
          --color-text-muted: #94A3B8 !important;

          --color-primary: #10B981 !important;
          --color-primary-dark: #059669 !important;
          --color-primary-soft: #1E3E35 !important;
          --color-primary-border: #34D399 !important;
          --color-accent: #34D399 !important;

          --color-good: #34D399 !important;
          --color-good-soft: #133328 !important;
          --color-good-border: #059669 !important;

          --color-warning: #FBBF24 !important;
          --color-warning-soft: #382408 !important;
          --color-warning-border: #D97706 !important;

          --color-alert: #F87171 !important;
          --color-alert-soft: #3B1414 !important;
          --color-alert-border: #DC2626 !important;

          --color-info: #60A5FA !important;
          --color-info-soft: #10243E !important;
          --color-info-border: #2563EB !important;

          --ks-bg: var(--color-bg) !important;
          --ks-surface: var(--color-surface) !important;
          --ks-surface-alt: var(--color-surface-alt) !important;
          --ks-surface-elevated: var(--color-surface-elevated) !important;
          --ks-border: var(--color-border) !important;
          --ks-border-subtle: var(--color-border-subtle) !important;
          --ks-border-focus: var(--color-border-focus) !important;
          --ks-text-primary: var(--color-text) !important;
          --ks-text-secondary: var(--color-text-secondary) !important;
          --ks-text-muted: var(--color-text-muted) !important;
          --ks-primary: var(--color-primary) !important;
          --ks-accent: var(--color-accent) !important;
          --ks-success: var(--color-good) !important;
          --ks-warning: var(--color-warning) !important;
          --ks-danger: var(--color-alert) !important;
          --ks-info: var(--color-info) !important;

          --shadow-card: 0 2px 8px rgba(0, 0, 0, 0.4), 0 12px 24px rgba(0, 0, 0, 0.5) !important;
          background-color: #0F1916 !important;
          color: #F8FAFC !important;
        }

        .stApp {
          background-color: #0F1916 !important;
          color: #F8FAFC !important;
        }

        /* --------------------------------------------------------------------------
           Streamlit Native Component Dark Mode Overrides
           -------------------------------------------------------------------------- */
        [data-baseweb="input"], [data-baseweb="base-input"] {
          background-color: #162723 !important;
          border-color: #2D4E45 !important;
          color: #F8FAFC !important;
        }
        [data-baseweb="input"] input, [data-baseweb="base-input"] input, textarea {
          color: #F8FAFC !important;
          background-color: transparent !important;
        }
        [data-baseweb="input"]:focus-within, [data-baseweb="base-input"]:focus-within {
          border-color: #34D399 !important;
        }
        [data-testid="stWidgetLabel"] label,
        [data-testid="stWidgetLabel"] p {
          color: #F8FAFC !important;
          font-weight: 600 !important;
        }
        [data-baseweb="select"] > div {
          background-color: #162723 !important;
          border-color: #2D4E45 !important;
          color: #F8FAFC !important;
        }
        [data-baseweb="select"] span {
          color: #F8FAFC !important;
        }
        [data-baseweb="popover"], [data-baseweb="menu"], [data-baseweb="menu"] ul {
          background-color: #162723 !important;
          color: #F8FAFC !important;
          border-color: #2D4E45 !important;
        }
        [data-baseweb="menu"] li {
          color: #F8FAFC !important;
        }
        [data-baseweb="menu"] li:hover, [data-baseweb="menu"] li[aria-selected="true"] {
          background-color: #1E352F !important;
          color: #34D399 !important;
        }
        [data-testid="stExpander"] {
          background-color: #162723 !important;
          border-color: #2D4E45 !important;
        }
        [data-testid="stExpander"] summary {
          color: #F8FAFC !important;
        }
        [data-testid="stExpander"] summary:hover {
          color: #34D399 !important;
        }
        [data-testid="stExpander"] [data-testid="stExpanderDetails"] {
          border-top: 1px solid #2D4E45 !important;
        }

        /* Tabs in Dark Mode */
        [data-testid="stTabs"] [data-baseweb="tab-list"] {
          border-bottom: 2px solid #2D4E45 !important;
        }
        [data-testid="stTabs"] [data-baseweb="tab"] {
          color: #CBD5E1 !important;
          font-weight: 600 !important;
        }
        [data-testid="stTabs"] [data-baseweb="tab"]:hover {
          color: #F8FAFC !important;
        }
        [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
          color: #34D399 !important;
          border-bottom-color: #34D399 !important;
          font-weight: 700 !important;
        }

        /* File Uploader in Dark Mode */
        [data-testid="stFileUploader"] {
          background-color: transparent !important;
        }
        [data-testid="stFileUploaderDropzone"] {
          background-color: #1E352F !important;
          border: 2px dashed #2D4E45 !important;
        }
        [data-testid="stFileUploaderDropzone"]:hover {
          border-color: #34D399 !important;
          background-color: #25413A !important;
        }
        [data-testid="stFileUploaderDropzoneInstructions"] {
          color: #F8FAFC !important;
        }
        [data-testid="stFileUploaderDropzoneInstructions"] span {
          color: #F8FAFC !important;
        }
        [data-testid="stFileUploaderDropzoneInstructions"] small {
          color: #CBD5E1 !important;
          font-weight: 500 !important;
        }
        [data-testid="stFileUploaderDropzone"] button {
          background-color: #162723 !important;
          border-color: #2D4E45 !important;
          color: #F8FAFC !important;
        }
        [data-testid="stFileUploaderDropzone"] button:hover {
          border-color: #34D399 !important;
          color: #34D399 !important;
          background-color: #1E352F !important;
        }
        [data-testid="stFileUploaderFile"] {
          background-color: #1E352F !important;
          border-color: #2D4E45 !important;
          color: #F8FAFC !important;
        }
        [data-testid="stFileUploaderFile"] div,
        [data-testid="stFileUploaderFile"] span {
          color: #F8FAFC !important;
        }
        [data-testid="stFileUploaderFile"] small {
          color: #CBD5E1 !important;
        }

        /* Camera Input in Dark Mode */
        [data-testid="stCameraInput"] {
          background-color: #162723 !important;
          border-color: #2D4E45 !important;
        }
        [data-testid="stCameraInput"] video {
          border-color: #2D4E45 !important;
        }
        [data-testid="stCameraInput"] button {
          background: linear-gradient(135deg, #10B981, #059669) !important;
          color: #FFFFFF !important;
          border-color: #34D399 !important;
        }

        /* Native Alerts in Dark Mode */
        [data-testid="stAlert"] {
          background-color: #162723 !important;
          border-color: #2D4E45 !important;
          color: #F8FAFC !important;
        }
        [data-testid="stAlert"] p {
          color: #F8FAFC !important;
        }

        /* Buttons in Dark Mode */
        .stButton > button {
          background-color: #162723 !important;
          border-color: #2D4E45 !important;
          color: #F8FAFC !important;
        }
        .stButton > button:hover {
          background-color: #1E352F !important;
          color: #34D399 !important;
          border-color: #34D399 !important;
        }
        /* Active navigation button in navbar */
        div[class*="st-key-nav_"] button:disabled {
          background: linear-gradient(135deg, #10B981, #059669) !important;
          color: #FFFFFF !important;
          border-color: #34D399 !important;
          font-weight: 700 !important;
          box-shadow: 0 2px 8px rgba(16, 185, 129, 0.35) !important;
          opacity: 1 !important;
          cursor: default !important;
        }
        /* Normal disabled buttons */
        .stButton > button:disabled:not([key*="nav_"]) {
          background-color: #1A2E28 !important;
          color: #94A3B8 !important;
          border-color: #223C35 !important;
          opacity: 0.55 !important;
        }
        /* Primary buttons */
        .stButton > button[kind="primary"],
        .stButton > button[data-testid="baseButton-primary"],
        .stFormSubmitButton > button {
          background: linear-gradient(135deg, #10B981, #059669) !important;
          color: #FFFFFF !important;
          font-weight: 700 !important;
          border: 1px solid #34D399 !important;
          box-shadow: 0 2px 10px rgba(16, 185, 129, 0.4) !important;
        }
        .stButton > button[kind="primary"]:hover,
        .stButton > button[data-testid="baseButton-primary"]:hover,
        .stFormSubmitButton > button:hover {
          background: linear-gradient(135deg, #059669, #047857) !important;
          color: #FFFFFF !important;
          box-shadow: 0 4px 14px rgba(16, 185, 129, 0.5) !important;
        }

        /* --------------------------------------------------------------------------
           KISANSENSE ASSISTANT (Native Charcoal-Green Dashboard Panel)
           -------------------------------------------------------------------------- */
        .assistant-dashboard-panel,
        .st-key-home_assistant_panel {
          background-color: #162723 !important;
          border: 1px solid #2D4E45 !important;
          border-radius: 14px !important;
          padding: 1.35rem 1.35rem 1.1rem 1.35rem !important;
          margin-top: 1rem !important;
          margin-bottom: 1.5rem !important;
          box-shadow: none !important;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:has(.st-key-home_assistant_panel),
        [data-testid="stVerticalBlockBorderWrapper"]:has(.assistant-dashboard-panel) {
          background-color: #162723 !important;
          border: 1px solid #2D4E45 !important;
          border-radius: 14px !important;
          box-shadow: none !important;
        }
        .assistant-header-icon {
          background-color: #1E352F !important;
          border: 1px solid #2D4E45 !important;
        }
        .assistant-title {
          color: #F8FAFC !important;
        }
        .assistant-subtitle {
          color: #CBD5E1 !important;
        }

        /* Prompt Chips */
        div[class*="st-key-chip_home_"] button,
        div[class*="st-key-chip_asst_"] button {
          background-color: #1E352F !important;
          border: 1px solid #2D4E45 !important;
          color: #F8FAFC !important;
          font-weight: 600 !important;
        }
        div[class*="st-key-chip_home_"] button:hover,
        div[class*="st-key-chip_asst_"] button:hover {
          background-color: #10B981 !important;
          border-color: #34D399 !important;
          color: #FFFFFF !important;
        }

        /* Chat Messages */
        [data-testid="stChatMessage"] {
          background-color: #18312C !important;
          border: 1px solid #2D4E45 !important;
          color: #F8FAFC !important;
        }
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-user"]),
        [data-testid="stChatMessage"][data-role="user"] {
          background-color: #1E352F !important;
          border-color: #2D4E45 !important;
          color: #F8FAFC !important;
        }
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-assistant"]),
        [data-testid="stChatMessage"][data-role="assistant"] {
          background-color: #162723 !important;
          border-color: #2D4E45 !important;
          border-left: 3px solid #10B981 !important;
          color: #F8FAFC !important;
        }
        [data-testid="stChatMessage"] p,
        [data-testid="stChatMessage"] div,
        [data-testid="stChatMessage"] span {
          color: #F8FAFC !important;
        }
        [data-testid="stChatMessage"] [data-testid="stChatMessageAvatarCustom"],
        [data-testid="stChatMessage"] [data-testid="chatAvatarIcon-assistant"],
        [data-testid="stChatMessage"] [data-testid="chatAvatarIcon-user"] {
          background-color: #1E352F !important;
          border: 1px solid #2D4E45 !important;
        }

        /* Chat Input Bar */
        [data-testid="stChatInput"] {
          background-color: #10201D !important;
          border: 1px solid #2D4E45 !important;
          border-radius: 12px !important;
        }
        [data-testid="stChatInput"]:focus-within {
          border-color: #34D399 !important;
          box-shadow: 0 0 0 1px #34D399 !important;
        }
        [data-testid="stChatInput"] textarea {
          color: #F8FAFC !important;
        }
        [data-testid="stChatInput"] textarea::placeholder {
          color: #94A3B8 !important;
        }
        [data-testid="stChatInput"] button,
        [data-testid="stChatInputSubmitButton"] {
          background-color: #10B981 !important;
          color: #FFFFFF !important;
        }
        [data-testid="stChatInput"] button:hover,
        [data-testid="stChatInputSubmitButton"]:hover {
          background-color: #34D399 !important;
          color: #0F1916 !important;
        }
        [data-testid="stChatInputInstructions"] {
          color: #94A3B8 !important;
        }

        /* --------------------------------------------------------------------------
           DASHBOARD HEROES & CARDS (Dark Theme Cohesion)
           -------------------------------------------------------------------------- */
        .farm-health-hero-good {
          background: linear-gradient(135deg, #162723 88%, #1E352F 100%) !important;
        }
        .farm-health-hero-warning {
          background: linear-gradient(135deg, #162723 88%, #382408 100%) !important;
        }
        .farm-health-hero-alert {
          background: linear-gradient(135deg, #162723 88%, #3B1414 100%) !important;
        }
        .farm-health-hero-critical {
          background: linear-gradient(135deg, #162723 88%, #450A0A 100%) !important;
        }
        .metric-card {
          background-color: #162723 !important;
          border-color: #2D4E45 !important;
        }
        .insight-card {
          background-color: #162723 !important;
          border-color: #2D4E45 !important;
        }
        .action-hero-card {
          background-color: #162723 !important;
          border-color: #2D4E45 !important;
        }
        .action-secondary-box {
          background-color: #1E352F !important;
          border-color: #2D4E45 !important;
          color: #F8FAFC !important;
        }
        .vision-card, .vision-guidance-item {
          background-color: #162723 !important;
          border-color: #2D4E45 !important;
          color: #F8FAFC !important;
        }
        .vision-section-box {
          background-color: #1E352F !important;
          border-color: #2D4E45 !important;
          color: #F8FAFC !important;
        }
        .vision-result-healthy {
          background: linear-gradient(135deg, #162723 88%, #1E352F 100%) !important;
        }
        .vision-result-warning {
          background: linear-gradient(135deg, #162723 88%, #382408 100%) !important;
        }
        .vision-result-rejected {
          background: linear-gradient(135deg, #162723 88%, #3B1414 100%) !important;
        }
        .weather-context-banner, .weather-metric-card, .weather-impact-card, .forecast-card, .weather-no-risks-card, .weather-assistant-box {
          background-color: #162723 !important;
          border-color: #2D4E45 !important;
          color: #F8FAFC !important;
        }
        .weather-action-hero {
          background-color: #162723 !important;
        }
        .weather-action-good {
          background: linear-gradient(135deg, #162723 88%, #1E352F 100%) !important;
          border-color: #34D399 !important;
        }
        .weather-action-warning {
          background: linear-gradient(135deg, #162723 88%, #382408 100%) !important;
          border-color: #FBBF24 !important;
        }
        .weather-action-alert {
          background: linear-gradient(135deg, #162723 88%, #3B1414 100%) !important;
          border-color: #F87171 !important;
        }
        .weather-risk-banner {
          background-color: #162723 !important;
        }
        .home-weather-banner {
          background-color: #162723 !important;
          border-color: #2D4E45 !important;
          color: #F8FAFC !important;
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
