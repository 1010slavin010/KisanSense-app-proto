"""Top navigation bar for KisanSense.

Uses session-state-driven routing rather than Streamlit's folder-based
multipage system, so the navbar's appearance stays fully under the
design system's control. Includes multilingual selector.
"""

from __future__ import annotations

import streamlit as st

from utils.config import APP_NAME, NAV_ITEMS
from utils.translations import DEFAULT_LANG, SUPPORTED_LANGUAGES, t


def _go_to(page_key: str) -> None:
    st.session_state.page = page_key


def _on_lang_change() -> None:
    selected = st.session_state.get("lang_selector")
    if selected and selected in SUPPORTED_LANGUAGES:
        st.session_state.lang = selected


def render_navbar(current_page: str) -> None:
    cols = st.columns([1.8, 1, 1.1, 1.1, 1, 1.1, 1, 1.4])

    with cols[0]:
        st.markdown(f'<div class="navbar-brand">{APP_NAME}</div>', unsafe_allow_html=True)

    for col, (key, _default_label) in zip(cols[1:7], NAV_ITEMS):
        with col:
            label = t(f"nav_{key}")
            st.button(
                label,
                key=f"nav_{key}",
                disabled=(key == current_page),
                on_click=_go_to,
                args=(key,),
                use_container_width=True,
            )

    with cols[7]:
        lang_keys = list(SUPPORTED_LANGUAGES.keys())
        current_lang = st.session_state.get("lang", DEFAULT_LANG)
        curr_idx = lang_keys.index(current_lang) if current_lang in lang_keys else 0
        st.selectbox(
            "Language",
            options=lang_keys,
            index=curr_idx,
            format_func=lambda k: SUPPORTED_LANGUAGES.get(k, k),
            key="lang_selector",
            on_change=_on_lang_change,
            label_visibility="collapsed",
        )

    st.markdown('<hr class="navbar-divider" />', unsafe_allow_html=True)
