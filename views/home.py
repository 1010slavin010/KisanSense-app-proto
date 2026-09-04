"""Home page: the main KisanSense dashboard.

Shows current farm conditions (soil, temperature, irrigation) and the
on-page "Ask KisanSense" assistant. This is the only fully built page
in Phase 1 — other sections are lightweight placeholders.
"""

import streamlit as st

from components.cards import render_metric_card
from components.chatbot import render_chatbot
from components.status import render_status_dot
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
    """Fetch (and cache for the session) the current mock sensor reading.

    Caching in session_state keeps the dashboard visually stable across
    reruns (e.g. sending a chat message) instead of jumping to a new
    random reading every time. Swap get_current_sensor_data() for a
    real data source later without touching this page.
    """
    if "sensor_reading" not in st.session_state:
        st.session_state.sensor_reading = get_current_sensor_data()
    return st.session_state.sensor_reading


def render() -> None:
    reading = _get_sensor_reading()

    st.markdown(f'<h1 class="hero-title">{APP_NAME}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="hero-tagline">{t("home_tagline")}</p>', unsafe_allow_html=True)
    render_status_dot(t("home_status_active"))

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

    soil_label, soil_type = get_soil_status(reading.soil_moisture)
    temp_label, temp_type = get_temperature_status(reading.temperature)
    irrigation = get_irrigation_status(reading.soil_moisture)

    col1, col2, col3 = st.columns(3)
    with col1:
        render_metric_card(
            title=t("card_soil_title"),
            value=format_percent(reading.soil_moisture),
            status_type=soil_type,
            status_label=soil_label,
            description="Based on the latest reading from your farm's soil sensor.",
            progress_fraction=reading.soil_moisture / 100,
        )
    with col2:
        render_metric_card(
            title=t("card_temp_title"),
            value=format_temperature(reading.temperature),
            status_type=temp_type,
            status_label=temp_label,
            description="Comfortable range for most crops is 15°C to 35°C.",
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
