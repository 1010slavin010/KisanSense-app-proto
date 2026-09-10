"""Assistant page: dedicated AI advisory workspace for KisanSense.

Provides direct access to the Smart Farm Intelligence-backed KisanSense Assistant,
grounded in live telemetry and active farm profile context.
"""

from __future__ import annotations

import streamlit as st

from components.chatbot import render_chatbot
from services.farm_service import get_farm_context, get_farm_profile, is_profile_configured
from services.sensor_service import get_current_sensor_data
from utils.translations import t


def render() -> None:
    profile = get_farm_profile()
    farm_ctx = get_farm_context()
    has_profile = is_profile_configured(profile)

    # Active reading from session state or sensor service
    reading = st.session_state.get("sensor_reading")
    if reading is None:
        reading = get_current_sensor_data(farm_context=farm_ctx)
        st.session_state.sensor_reading = reading

    # Farm Context Pill
    if has_profile:
        variety_text = f" ({profile.crop_variety})" if profile.crop_variety else ""
        stage_part = f" • 🌱 {profile.growth_stage}" if profile.growth_stage else ""
        soil_part = f" • 🧱 {profile.soil_type}" if profile.soil_type else ""
        moist_part = f" • 💧 {reading.soil_moisture:.0f}% moisture" if reading and reading.is_online else ""

        st.markdown(
            f"""
            <div style="margin-bottom: 1.2rem; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                <span class="badge badge-good" style="font-size: 0.88rem; padding: 0.35rem 0.8rem;">
                    🌾 {profile.crop}{variety_text}
                </span>
                <span style="color: var(--color-text-muted); font-size: 0.9rem;">
                    {stage_part}{soil_part}{moist_part}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Render Assistant Chatbot
    render_chatbot(reading=reading, farm_context=farm_ctx)
