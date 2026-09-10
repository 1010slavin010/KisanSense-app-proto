"""Status indicator component for KisanSense.

Displays a semantic status dot alongside clear text labels, ensuring
status is never communicated by color alone.
"""

from __future__ import annotations

import streamlit as st


def render_status_dot(label: str, status_type: str = "good") -> None:
    dot_class = f"status-dot status-dot-{status_type}" if status_type != "good" else "status-dot"
    st.markdown(
        f"""
        <div class="status-dot-row">
            <span class="{dot_class}"></span>
            <span class="status-dot-label">{label}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
