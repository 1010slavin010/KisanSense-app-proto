"""KisanSense — Main application entry point.

Handles page configuration, global styling, session-state initialization,
and navigation between pages while preserving top navbar control.
"""

import streamlit as st

from components.navbar import render_navbar
from services.farm_service import init_farm_profile
from utils.config import APP_NAME, PAGE_ICON
from utils.translations import DEFAULT_LANG
from views import alerts, assistance, farm, home, irrigation, vision

PAGES = {
    "home": home,
    "farm": farm,
    "irrigation": irrigation,
    "vision": vision,
    "assistant": assistance,
    "alerts": alerts,
}


def load_css(path: str) -> None:
    """Inject the app's design system. Styling only — safe to skip if missing."""
    try:
        with open(path, "r", encoding="utf-8") as css_file:
            st.markdown(f"<style>{css_file.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass


def init_session_state() -> None:
    if "page" not in st.session_state:
        st.session_state.page = "home"
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []
    if "lang" not in st.session_state:
        st.session_state.lang = DEFAULT_LANG
    if "sim_condition" not in st.session_state:
        st.session_state.sim_condition = "NORMAL"
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
