"""Home page: the main KisanSense dashboard.

Shows current farm conditions (soil, temperature, irrigation), active farm context,
alerts when action is needed, and the on-page "Ask KisanSense" assistant.
Works seamlessly both with and without a configured farm profile.
"""

from __future__ import annotations

import streamlit as st

from components.cards import render_metric_card
from components.chatbot import render_chatbot
from components.status import render_status_dot
from services.farm_service import (
    get_farm_context,
    get_farm_profile,
    is_profile_configured,
)
from services.irrigation_service import get_irrigation_status
from services.sensor_service import get_current_sensor_data
from utils.config import APP_NAME
from utils.helpers import (
    format_percent,
    format_temperature,
    get_soil_status,
    get_temperature_status,
)
from utils.translations import t


def _get_sensor_reading():
    """Fetch (and cache for the session) the current mock sensor reading."""
    if "sensor_reading" not in st.session_state:
        st.session_state.sensor_reading = get_current_sensor_data()
    return st.session_state.sensor_reading


def render() -> None:
    reading = _get_sensor_reading()
    profile = get_farm_profile()
    farm_ctx = get_farm_context()
    has_profile = is_profile_configured(profile)

    # Header section
    st.markdown(f'<h1 class="hero-title">{APP_NAME}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="hero-tagline">{t("home_tagline")}</p>', unsafe_allow_html=True)

    header_cols = st.columns([2, 3])
    with header_cols[0]:
        render_status_dot(t("home_status_active"))

    # Active Farm Context Bar or Empty Prompt
    if has_profile:
        variety_text = f" ({profile.crop_variety})" if profile.crop_variety else ""
        location_part = f" • 📍 {profile.location}" if profile.location else ""
        stage_part = f" • 🌱 {profile.growth_stage}" if profile.growth_stage else ""
        method_part = f" • 💧 {profile.irrigation_method}" if profile.irrigation_method else ""

        st.markdown(
            f"""
            <div style="margin-top: 0.6rem; margin-bottom: 0.4rem; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                <span class="badge badge-good" style="font-size: 0.88rem; padding: 0.3rem 0.75rem;">
                    🌾 {profile.crop}{variety_text}
                </span>
                <span style="color: var(--color-text-muted); font-size: 0.9rem;">
                    {location_part}{stage_part}{method_part}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
        col_p1, col_p2 = st.columns([3.5, 1.2])
        with col_p1:
            st.info(f"💡 {t('home_empty_profile_prompt')}")
        with col_p2:
            if st.button(f"⚙️ {t('home_setup_profile_btn')}", key="btn_home_setup_profile", use_container_width=True):
                st.session_state.page = "farm"
                st.rerun()

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

    # Status computation
    soil_label, soil_type = get_soil_status(reading.soil_moisture)
    temp_label, temp_type = get_temperature_status(reading.temperature)
    irrigation = get_irrigation_status(reading.soil_moisture, farm_context=farm_ctx)

    # Important Alerts banner if water is needed
    if irrigation.needs_water:
        crop_target = f" for your {profile.crop}" if has_profile and profile.crop else ""
        st.warning(
            f"⚠️ **{t('home_alerts_title')}**: {t('home_alert_water_needed')}{crop_target} "
            f"(Soil moisture is at {format_percent(reading.soil_moisture)})."
        )

    # Metric cards row
    col1, col2, col3 = st.columns(3)
    with col1:
        render_metric_card(
            title=t("card_soil_title"),
            value=format_percent(reading.soil_moisture),
            status_type=soil_type,
            status_label=t(f"status_{soil_label.lower()}"),
            description=t("card_soil_desc"),
            progress_fraction=reading.soil_moisture / 100,
        )
    with col2:
        render_metric_card(
            title=t("card_temp_title"),
            value=format_temperature(reading.temperature),
            status_type=temp_type,
            status_label=t(f"status_{temp_label.lower()}"),
            description=t("card_temp_desc"),
        )
    with col3:
        render_metric_card(
            title=t("card_irrigation_title"),
            value=irrigation.label,
            status_type=irrigation.status_type,
            description=irrigation.detail,
        )

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
    render_chatbot()
