"""KisanSense — Main application entry point.

Handles page configuration, global styling, session-state initialization,
and navigation between pages while preserving top navbar control.
"""

import streamlit as st

from components.navbar import render_navbar
from services.farm_service import init_farm_profile
from utils.config import APP_NAME, PAGE_ICON
from utils.translations import DEFAULT_LANG
from views import alerts, analytics, assistance, devices, farm, home, irrigation, vision, weather

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
          --color-bg: #111614 !important;
          --color-surface: #1B2320 !important;
          --color-surface-alt: #222C28 !important;
          --color-border: #2D3B34 !important;
          --color-text: #F1F5F3 !important;
          --color-text-muted: #9BB0A5 !important;

          --color-primary: #3EA082 !important;
          --color-primary-soft: #1A382C !important;

          --color-good: #52B775 !important;
          --color-good-soft: #183824 !important;
          --color-warning: #E5A43B !important;
          --color-warning-soft: #382A14 !important;
          --color-alert: #E5684A !important;
          --color-alert-soft: #3D1F17 !important;

          --shadow-card: 0 2px 8px rgba(0, 0, 0, 0.4), 0 12px 24px rgba(0, 0, 0, 0.5) !important;
          background-color: #111614 !important;
          color: #F1F5F3 !important;
        }

        .stApp {
          background-color: #111614 !important;
          color: #F1F5F3 !important;
        }

        /* Streamlit native widget styling in dark mode */
        [data-baseweb="input"], [data-baseweb="base-input"] {
          background-color: #1B2320 !important;
          border-color: #2D3B34 !important;
          color: #F1F5F3 !important;
        }
        [data-baseweb="input"] input, [data-baseweb="base-input"] input, textarea {
          color: #F1F5F3 !important;
          background-color: transparent !important;
        }
        [data-baseweb="select"] > div {
          background-color: #1B2320 !important;
          border-color: #2D3B34 !important;
          color: #F1F5F3 !important;
        }
        [data-baseweb="select"] span {
          color: #F1F5F3 !important;
        }
        [data-baseweb="popover"], [data-baseweb="menu"], [data-baseweb="menu"] ul {
          background-color: #1B2320 !important;
          color: #F1F5F3 !important;
          border-color: #2D3B34 !important;
        }
        [data-baseweb="menu"] li {
          color: #F1F5F3 !important;
        }
        [data-baseweb="menu"] li:hover, [data-baseweb="menu"] li[aria-selected="true"] {
          background-color: #1A382C !important;
        }
        [data-testid="stChatMessage"] {
          background-color: #1B2320 !important;
          border-color: #2D3B34 !important;
          color: #F1F5F3 !important;
        }
        [data-testid="stChatInput"] {
          background-color: #1B2320 !important;
          border-color: #2D3B34 !important;
        }
        [data-testid="stChatInput"] textarea {
          color: #F1F5F3 !important;
          background-color: transparent !important;
        }
        [data-testid="stExpander"] {
          background-color: #1B2320 !important;
          border-color: #2D3B34 !important;
        }
        [data-testid="stExpander"] summary {
          color: #F1F5F3 !important;
        }
        [data-testid="stExpander"] summary:hover {
          color: #3EA082 !important;
        }
        .stButton > button {
          border-color: #2D3B34 !important;
          color: #9BB0A5 !important;
        }
        .stButton > button:hover {
          background-color: #1A382C !important;
          color: #3EA082 !important;
          border-color: #3EA082 !important;
        }
        .stButton > button:disabled {
          background-color: #3EA082 !important;
          color: #111614 !important;
          border-color: #3EA082 !important;
          font-weight: 600 !important;
        }
        .farm-health-hero-good {
          background: linear-gradient(135deg, #1B2320 88%, #142a1d 100%) !important;
        }
        .farm-health-hero-warning {
          background: linear-gradient(135deg, #1B2320 88%, #2d2010 100%) !important;
        }
        .farm-health-hero-alert {
          background: linear-gradient(135deg, #1B2320 88%, #2d1812 100%) !important;
        }
        .farm-health-hero-critical {
          background: linear-gradient(135deg, #1B2320 88%, #361414 100%) !important;
        }
        .metric-card {
          background-color: #1B2320 !important;
          border-color: #2D3B34 !important;
        }
        .insight-card {
          background-color: #1B2320 !important;
          border-color: #2D3B34 !important;
        }
        .action-hero-card {
          background-color: #1B2320 !important;
          border-color: #2D3B34 !important;
        }
        .action-secondary-box {
          background-color: #222C28 !important;
          border-color: #2D3B34 !important;
          color: #F1F5F3 !important;
        }
        .vision-card, .vision-guidance-item {
          background-color: #1B2320 !important;
          border-color: #2D3B34 !important;
          color: #F1F5F3 !important;
        }
        .vision-section-box {
          background-color: #222C28 !important;
          border-color: #2D3B34 !important;
          color: #F1F5F3 !important;
        }
        .vision-result-healthy {
          background: linear-gradient(135deg, #1B2320 88%, #142a1d 100%) !important;
        }
        .vision-result-warning {
          background: linear-gradient(135deg, #1B2320 88%, #2d2010 100%) !important;
        }
        .vision-result-rejected {
          background: linear-gradient(135deg, #1B2320 88%, #2d1812 100%) !important;
        }
        .weather-context-banner, .weather-metric-card, .weather-impact-card, .forecast-card, .weather-no-risks-card, .weather-assistant-box {
          background-color: #1B2320 !important;
          border-color: #2D3B34 !important;
          color: #F1F5F3 !important;
        }
        .weather-action-hero {
          background-color: #1B2320 !important;
        }
        .weather-action-good {
          background: linear-gradient(135deg, #1B2320 88%, #142a1d 100%) !important;
          border-color: #52B775 !important;
        }
        .weather-action-warning {
          background: linear-gradient(135deg, #1B2320 88%, #2d2010 100%) !important;
          border-color: #E5A43B !important;
        }
        .weather-action-alert {
          background: linear-gradient(135deg, #1B2320 88%, #2d1812 100%) !important;
          border-color: #E5684A !important;
        }
        .weather-risk-banner {
          background-color: #1B2320 !important;
        }
        .home-weather-banner {
          background-color: #1B2320 !important;
          border-color: #2D3B34 !important;
          color: #F1F5F3 !important;
        }
        </style>
        """
        st.markdown(dark_css, unsafe_allow_html=True)


def init_session_state() -> None:
    if "page" not in st.session_state:
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
    st.set_page_config(
        page_title=APP_NAME,
        page_icon=PAGE_ICON,
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    init_session_state()
    load_css("assets/style.css")

    render_navbar(current_page=st.session_state.page)

    page_module = PAGES.get(st.session_state.page, home)
    page_module.render()


if __name__ == "__main__":
    main()
