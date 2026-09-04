"""Reusable status card rendering for the KisanSense dashboard.

Cards are rendered as single HTML blocks so the design system in
assets/style.css has full control over layout. No business logic
lives here — callers pass already-computed status labels/types.
"""

from __future__ import annotations

import streamlit as st


def render_metric_card(
    title: str,
    value: str,
    status_type: str,
    description: str,
    status_label: str | None = None,
    progress_fraction: float | None = None,
) -> None:
    badge_html = (
        f'<span class="badge badge-{status_type}">{status_label}</span>'
        if status_label
        else ""
    )

    progress_html = ""
    if progress_fraction is not None:
        pct = max(0.0, min(1.0, progress_fraction)) * 100
        progress_html = (
            '<div class="metric-progress-track">'
            f'<div class="metric-progress-fill metric-progress-{status_type}" '
            f'style="width: {pct:.0f}%;"></div>'
            "</div>"
        )

    st.markdown(
        f"""
        <div class="metric-card metric-card-{status_type}">
            <div class="metric-card-title">{title}</div>
            <div class="metric-card-value">{value}</div>
            {badge_html}
            {progress_html}
            <p class="metric-card-description">{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
