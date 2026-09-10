"""Farm Analytics and Telemetry Trends page for KisanSense.

Visualizes genuine soil moisture trends, temperature/humidity dynamics,
and field connectivity uptime. Uses only actual session-stored telemetry observations.
"""

from __future__ import annotations

from datetime import datetime
import streamlit as st

from components.cards import render_metric_card
from components.status import render_status_dot
from services.farm_service import get_farm_profile
from services.sensor_service import MODE_HARDWARE, get_current_sensor_data
from services.timeline_service import get_timeline_events
from utils.translations import t


def _record_telemetry_point(reading) -> list[dict]:
    """Maintain a rolling telemetry buffer of genuine observations in session state."""
    if "telemetry_history" not in st.session_state:
        st.session_state.telemetry_history = []

    if reading and reading.is_online:
        now_str = datetime.now().strftime("%H:%M")
        hist = st.session_state.telemetry_history
        if (
            not hist
            or hist[-1].get("time") != now_str
            or hist[-1].get("soil_moisture") != reading.soil_moisture
        ):
            hist.append(
                {
                    "time": now_str,
                    "soil_moisture": round(reading.soil_moisture, 1),
                    "temperature": round(reading.temperature, 1),
                    "humidity": round(reading.humidity, 1),
                    "is_online": True,
                }
            )
            if len(hist) > 25:
                st.session_state.telemetry_history = hist[-25:]

    return st.session_state.telemetry_history


def render() -> None:
    profile = get_farm_profile()
    crop_title = profile.crop if (profile and profile.crop) else "General Crop"

    sim_condition = st.session_state.get("sim_condition", "NORMAL")
    reading = get_current_sensor_data(condition=sim_condition)
    history = _record_telemetry_point(reading)

    st.markdown(f'<h1 class="hero-title">📈 {t("analytics_header_title")}</h1>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="hero-tagline">{t("analytics_header_subtitle")} ({crop_title})</p>',
        unsafe_allow_html=True,
    )

    col_s1, col_s2 = st.columns([2, 3])
    with col_s1:
        render_status_dot(t("home_status_active"))
    with col_s2:
        source_label = (
            t("sensor_source_hardware")
            if reading.source == MODE_HARDWARE
            else t("sensor_source_simulation")
        )
        st.markdown(
            f'<div class="status-dot-row" style="justify-content: flex-end;">'
            f'<span class="status-dot status-dot-good"></span>'
            f'<span>Telemetry Stream: <strong>Active</strong> ({source_label})</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)

    # 4 Overview KPI cards
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        avg_sm = sum(p["soil_moisture"] for p in history) / len(history) if history else (reading.soil_moisture if reading.is_online else 0.0)
        render_metric_card(
            title=t("analytics_avg_moisture"),
            value=f"{avg_sm:.1f}%",
            status_type="good" if 30.0 <= avg_sm <= 60.0 else "warning",
            status_label="Balanced" if 30.0 <= avg_sm <= 60.0 else "Attention",
            description="Mean observed soil moisture.",
            progress_fraction=avg_sm / 100,
        )

    with k2:
        avg_t = sum(p["temperature"] for p in history) / len(history) if history else (reading.temperature if reading.is_online else 0.0)
        render_metric_card(
            title=t("analytics_avg_temp"),
            value=f"{avg_t:.1f}°C",
            status_type="good" if 15.0 <= avg_t <= 35.0 else "warning",
            status_label="Favorable" if 15.0 <= avg_t <= 35.0 else "Elevated",
            description="Mean canopy temperature.",
        )

    with k3:
        uptime_pct = 100.0 if reading.is_online else 0.0
        render_metric_card(
            title=t("analytics_uptime"),
            value=f"{uptime_pct:.0f}%",
            status_type="good" if reading.is_online else "alert",
            status_label="Online" if reading.is_online else "Offline",
            description="Sensor packet transmission rate.",
            progress_fraction=1.0 if reading.is_online else 0.0,
        )

    with k4:
        obs_count = len(history)
        render_metric_card(
            title="TELEMETRY READINGS",
            value=f"{obs_count}",
            status_type="info",
            status_label="Logged",
            description="Readings recorded in this session.",
        )

    st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)

    # Restrained Trends Charts
    st.markdown(f'<div class="insights-header">📊 Telemetry Trends</div>', unsafe_allow_html=True)
    if len(history) >= 2:
        col_ch1, col_ch2 = st.columns(2)

        with col_ch1:
            st.markdown(
                """
                <div class="insight-card" style="margin-bottom: 0.5rem; padding: 0.65rem 0.85rem;">
                    <div style="font-weight: 650; font-size: 0.9rem;">Soil Moisture Trend (%)</div>
                    <div style="font-size: 0.8rem; color: var(--color-text-secondary);">Target: 30% (Irrigate threshold) to 60% (Saturated cutoff).</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            chart_data = {
                "Time": [p["time"] for p in history],
                "Soil Moisture (%)": [p["soil_moisture"] for p in history],
            }
            st.line_chart(chart_data, x="Time", y="Soil Moisture (%)", color="#1F5C52")

        with col_ch2:
            st.markdown(
                """
                <div class="insight-card" style="margin-bottom: 0.5rem; padding: 0.65rem 0.85rem;">
                    <div style="font-weight: 650; font-size: 0.9rem;">Temperature (°C) & Humidity (%) Trend</div>
                    <div style="font-size: 0.8rem; color: var(--color-text-secondary);">Canopy thermal and atmospheric moisture dynamics.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            chart_data_climate = {
                "Time": [p["time"] for p in history],
                "Temperature (°C)": [p["temperature"] for p in history],
                "Humidity (%)": [p["humidity"] for p in history],
            }
            st.line_chart(chart_data_climate, x="Time", y=["Temperature (°C)", "Humidity (%)"], color=["#C58A1A", "#3B6EA8"])
    else:
        st.info("Not enough telemetry data yet. As sensor readings are recorded over time, trends will plot automatically.")

    st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)

    # Recent Farm Activity Log
    st.markdown(f'<div class="insights-header">⏱️ {t("analytics_log_title")}</div>', unsafe_allow_html=True)
    events = get_timeline_events(limit=6)
    if events:
        for evt in events:
            st.markdown(
                f"""
                <div class="home-weather-banner" style="margin-bottom: 0.4rem; padding: 0.6rem 0.9rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
                        <div>
                            <span style="font-size: 1.05rem; margin-right: 6px;">{evt.icon}</span>
                            <span style="font-weight: 700; font-size: 0.9rem;">{evt.title}</span>
                            <span style="color: var(--color-text-secondary); font-size: 0.86rem; margin-left: 8px;">— {evt.description}</span>
                        </div>
                        <div style="font-size: 0.8rem; color: var(--color-text-muted);">
                            🕒 {evt.timestamp}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Not enough historical data yet. As events and telemetry are recorded, activity entries will appear here.")
