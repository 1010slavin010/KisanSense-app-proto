"""Breadcrumb navigation component for KisanSense.

Provides subtle, accessible, mobile-friendly breadcrumbs for all non-home pages.
"""

from __future__ import annotations

import streamlit as st


def render_breadcrumbs(current_page_title: str, current_page_key: str = "") -> None:
    """Render subtle, accessible breadcrumbs.
    
    Omitted entirely on the Home page (Phase 8 requirement: Home must not display 'Home / Home').
    """
    if current_page_key == "home" or current_page_title.lower() in ("home", "how is your farm?"):
        return

    breadcrumb_html = f"""
    <nav aria-label="Breadcrumb" class="ks-breadcrumb" style="margin-bottom: 14px; font-size: 0.84rem; color: var(--color-text-muted); display: flex; align-items: center; gap: 6px;">
        <a href="?page=home" target="_self" class="ks-breadcrumb-link" style="color: var(--color-primary); text-decoration: none; font-weight: 500;">Home</a>
        <span class="ks-breadcrumb-separator" aria-hidden="true" style="color: var(--color-text-muted); opacity: 0.6;">/</span>
        <span class="ks-breadcrumb-current" aria-current="page" style="font-weight: 600; color: var(--color-text);">{current_page_title}</span>
    </nav>
    """
    st.markdown(breadcrumb_html, unsafe_allow_html=True)
