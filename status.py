"""Small status indicator component (the "farm monitoring active" dot)."""

import streamlit as st


def render_status_dot(label: str) -> None:
    st.markdown(
        f"""
        <div class="status-dot-row">
            <span class="status-dot"></span>
            <span class="status-dot-label">{label}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
