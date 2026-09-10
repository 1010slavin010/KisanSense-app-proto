"""Assistant page: dedicated AI advisory workspace for KisanSense.

Provides direct access to the Smart Farm Intelligence-backed KisanSense Assistant,
grounded in live telemetry and active farm profile context.
"""

from __future__ import annotations

import streamlit as st

from components.breadcrumbs import render_breadcrumbs
from components.chatbot import render_chatbot
from services.ai_service import get_ai_response
from services.farm_service import get_farm_context, get_farm_profile, is_profile_configured
from services.sensor_service import get_current_sensor_data
from utils.translations import t


def render() -> None:
    profile = get_farm_profile()
    farm_ctx = get_farm_context()
    has_profile = is_profile_configured(profile)

    render_breadcrumbs("KisanSense Assistant", "assistant")

    reading = st.session_state.get("sensor_reading")
    if reading is None:
        reading = get_current_sensor_data(farm_context=farm_ctx)
        st.session_state.sensor_reading = reading

    st.markdown('<h1 class="ks-page-title hero-title">💬 KisanSense Assistant</h1>', unsafe_allow_html=True)
    st.markdown(
        '<p class="hero-tagline">AI-powered agronomic advisory grounded in your live farm telemetry, soil conditions, and crop profile.</p>',
        unsafe_allow_html=True,
    )

    # Farm Context Pill
    if has_profile:
        variety_text = f" ({profile.crop_variety})" if profile.crop_variety else ""
        stage_part = f" • 🌱 {profile.growth_stage}" if profile.growth_stage else ""
        soil_part = f" • 🪨 {profile.soil_type}" if profile.soil_type else ""
        moist_part = f" • 💧 {reading.soil_moisture:.0f}% moisture" if reading and reading.is_online else ""

        st.markdown(
            f"""
            <div style="margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                <span class="badge badge-good">
                    🌾 {profile.crop}{variety_text}
                </span>
                <span style="color: var(--color-text-secondary); font-size: 0.88rem;">
                    {stage_part}{soil_part}{moist_part}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Suggested question chips
    chip_cols = st.columns(4)
    chips = [
        (chip_cols[0], t("home_chip_water"), "Should I water my crop?"),
        (chip_cols[1], t("home_chip_soil"), "How is my soil?"),
        (chip_cols[2], t("home_chip_today"), "What should I do today?"),
        (chip_cols[3], t("home_chip_stress"), "Is my crop under stress?"),
    ]

    for col, label, query in chips:
        with col:
            if st.button(label, key=f"chip_asst_{query[:8]}", use_container_width=True):
                st.session_state.chat_messages.append({"role": "user", "content": query})
                ctx = {
                    "page": "assistant",
                    **farm_ctx,
                    "reading": reading,
                    "soil_moisture": reading.soil_moisture if reading else None,
                    "temperature": reading.temperature if reading else None,
                    "humidity": reading.humidity if reading else None,
                    "sensor_online": reading.is_online if reading else True,
                    "vision_result": st.session_state.get("latest_vision_result"),
                    "weather": st.session_state.get("latest_weather_snapshot"),
                }
                reply = get_ai_response(query, context=ctx)
                st.session_state.chat_messages.append({"role": "assistant", "content": reply})
                st.rerun()

    # Render Assistant Chatbot
    render_chatbot(reading=reading, farm_context=farm_ctx, show_header=False)
