"""Top navigation bar for KisanSense.

Uses session-state-driven routing rather than Streamlit's folder-based
multipage system, so the navbar's appearance stays fully under the
design system's control (see app.py for why views/ is not named
pages/).
"""

import streamlit as st

from utils.config import APP_NAME, NAV_ITEMS


def _go_to(page_key: str) -> None:
    st.session_state.page = page_key


def render_navbar(current_page: str) -> None:
    cols = st.columns([2, 1, 1, 1, 1, 1, 1])

    with cols[0]:
        st.markdown(f'<div class="navbar-brand">{APP_NAME}</div>', unsafe_allow_html=True)

    for col, (key, label) in zip(cols[1:], NAV_ITEMS):
        with col:
            st.button(
                label,
                key=f"nav_{key}",
                disabled=(key == current_page),
                on_click=_go_to,
                args=(key,),
                use_container_width=True,
            )

    st.markdown('<hr class="navbar-divider" />', unsafe_allow_html=True)
