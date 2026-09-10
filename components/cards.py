"""Reusable metric card component for KisanSense.

Follows the agricultural technology design system:
- Small uppercase label
- Prominent legible value
- Semantic status badge (dot + text label)
- Optional subtle progress track
- Concise descriptive context
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
    badge_html = ""
    if status_label:
        badge_html = f'<div style="margin-bottom: 0.35rem;"><span class="badge badge-{status_type}">● {status_label}</span></div>'

    progress_html = ""
    if progress_fraction is not None:
        pct = max(0.0, min(1.0, progress_fraction)) * 100
        progress_html = (
            '<div class="metric-progress-track">'
            f'<div class="metric-progress-fill metric-progress-{status_type}" '
            f'style="width: {pct:.0f}%;"></div>'
            "</div>"
        )

    elements = [
        f'<div class="metric-card metric-card-{status_type}">',
        f'<div class="metric-card-title">{title}</div>',
        f'<div class="metric-card-value">{value}</div>',
    ]
    if badge_html:
        elements.append(badge_html)
    if progress_html:
        elements.append(progress_html)
    elements.append(f'<p class="metric-card-description">{description}</p>')
    elements.append('</div>')

    st.markdown("".join(elements), unsafe_allow_html=True)
