"""Top navigation bar for KisanSense.

Uses session-state-driven routing rather than Streamlit's folder-based
multipage system, so the navbar's appearance stays fully under the
design system's control. Includes multilingual selector, theme toggle,
and contextual active alert counter.
"""

from __future__ import annotations

import streamlit as st

from utils.config import APP_NAME, NAV_ITEMS
from utils.translations import DEFAULT_LANG, SUPPORTED_LANGUAGES, t


def _go_to(page_key: str) -> None:
    st.session_state.page = page_key
    try:
        st.query_params["page"] = page_key
    except Exception:
        pass


def _on_lang_change() -> None:
    selected = st.session_state.get("lang_selector")
    if selected and selected in SUPPORTED_LANGUAGES:
        st.session_state.lang = selected


def _toggle_theme() -> None:
    current = st.session_state.get("theme", "light")
    st.session_state.theme = "dark" if current == "light" else "light"


def _get_active_alert_count() -> int:
    """Check active alert count from latest sensor telemetry for navigation indicator."""
    reading = st.session_state.get("sensor_reading")
    if reading is None:
        return 0
    count = 0
    if not reading.is_online:
        count += 1
    if reading.battery_voltage and reading.battery_voltage < 3.4:
        count += 1
    if reading.soil_moisture < 30.0:
        count += 1
    elif reading.soil_moisture > 75.0:
        count += 1
    return count


def render_navbar(current_page: str) -> None:
    # -------------------------------------------------------------------------
    # Top Header Bar: Brand Identity on Left, Controls (Lang + Theme) on Right
    # -------------------------------------------------------------------------
    col_brand, col_lang, col_theme = st.columns([4.2, 1.4, 1.2])

    with col_brand:
        st.markdown(
            f'<div class="navbar-brand">'
            f'<span>🌱 {APP_NAME}</span>'
            f'<span style="font-size: 0.8rem; font-weight: 500; color: var(--color-text-muted); margin-left: 8px;">'
            f'Smart Farming'
            f'</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col_lang:
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

    with col_theme:
        current_theme = st.session_state.get("theme", "light")
        theme_icon = "🌙" if current_theme == "light" else "☀️"
        theme_target_label = t("theme_dark") if current_theme == "light" else t("theme_light")
        st.button(
            f"{theme_icon} {theme_target_label}",
            key="btn_theme_toggle",
            help=t("theme_toggle_help"),
            on_click=_toggle_theme,
            use_container_width=True,
        )

    # -------------------------------------------------------------------------
    # Primary Navigation Row: 9 Clean Functional Buttons
    # -------------------------------------------------------------------------
    alert_count = _get_active_alert_count()
    nav_cols = st.columns(len(NAV_ITEMS))

    for col, (key, _default_label) in zip(nav_cols, NAV_ITEMS):
        with col:
            base_label = t(f"nav_{key}")
            if key == "alerts" and alert_count > 0:
                label = f"{base_label} ({alert_count})"
            else:
                label = base_label

            st.button(
                label,
                key=f"nav_{key}",
                disabled=(key == current_page),
                on_click=_go_to,
                args=(key,),
                use_container_width=True,
            )

    st.markdown('<hr class="navbar-divider" />', unsafe_allow_html=True)
