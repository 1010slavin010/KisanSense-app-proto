"""Custom 404 Not Found view for KisanSense.

Provides an application-level not-found state with clean branding and direct recovery actions.
"""

from __future__ import annotations

import streamlit as st
from utils.config import APP_NAME


def render() -> None:
    """Render the KisanSense 404 Page Not Found view."""
    st.markdown(
        f"""
        <div style="text-align: center; padding: 48px 16px; max-width: 600px; margin: 0 auto;">
            <div style="display: inline-flex; align-items: center; justify-content: center; width: 64px; height: 64px; border-radius: 16px; background-color: var(--color-primary-soft, #E8F1EE); color: var(--color-primary, #1F5C52); font-size: 32px; margin-bottom: 20px;">
                🌱
            </div>
            <div style="display: inline-block; font-size: 0.85rem; font-weight: 700; color: var(--color-warning, #C58A1A); text-transform: uppercase; letter-spacing: 0.08em; background: rgba(197, 138, 26, 0.12); padding: 4px 12px; border-radius: 12px; margin-bottom: 12px;">
                404
            </div>
            <h1 class="ks-page-title" style="font-size: 2rem; font-weight: 700; margin: 0 0 12px 0; color: var(--color-text, #17211F);">Page not found</h1>
            <p style="font-size: 1.05rem; color: var(--color-text-muted, #5E6B67); margin: 0 0 32px 0; line-height: 1.5;">
                The page you're looking for doesn't exist or may have moved.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_space_l, col_home, col_farm, col_space_r = st.columns([1.5, 2, 2, 1.5])
    with col_home:
        if st.button("Go Home", key="btn_404_home", type="primary", use_container_width=True):
            st.session_state.page = "home"
            st.query_params["page"] = "home"
            st.rerun()

    with col_farm:
        if st.button("Open Farm", key="btn_404_farm", type="secondary", use_container_width=True):
            st.session_state.page = "farm"
            st.query_params["page"] = "farm"
            st.rerun()
