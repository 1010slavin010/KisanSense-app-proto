"""KisanSense — Phase 1 entry point.

Handles page configuration, global styling, and session-state-based
navigation between pages.

The project intentionally uses views/ instead of Streamlit's special
pages/ directory so the custom top navigation remains in control.
"""

import streamlit as st

from components.navbar import render_navbar
from utils.config import APP_NAME, PAGE_ICON
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
