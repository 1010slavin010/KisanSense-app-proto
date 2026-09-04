"""Shared "coming soon" card for sections not yet built in Phase 1."""

import streamlit as st


def render_placeholder(title: str, description: str, planned_note: str) -> None:
    st.markdown(
        f"""
        <div class="placeholder-card">
            <h2 class="placeholder-title">{title}</h2>
            <p class="placeholder-description">{description}</p>
            <p class="placeholder-note">{planned_note}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
