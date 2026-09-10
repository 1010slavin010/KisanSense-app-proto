"""Farm Analytics and Telemetry Trends page for KisanSense.

Visualizes soil moisture trends, temperature/humidity dynamics,
irrigation recommendation history, plant health scans, and link stability.
"""

from __future__ import annotations

from datetime import datetime, timedelta
import streamlit as st

from components.cards import render_metric_card
from components.status import render_status_dot
from services.farm_service import get_farm_profile
from services.sensor_service import MODE_HARDWARE, get_current_sensor_data
from services.timeline_service import get_timeline_events
from utils.helpers import format_percent, format_temperature
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
            if len(hist) > 20:
                st.session_state.telemetry_history = hist[-20:]

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
            f'<span class="status-dot" style="background-color: var(--color-good);"></span>'
            f'<span class="status-dot-label">Analytics Stream: <strong>Active</strong> ({source_label})</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)

    # Overview KPI row
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        avg_sm = sum(p["soil_moisture"] for p in history) / len(history) if history else (reading.soil_moisture if reading.is_online else 0.0)
        render_metric_card(
            title=f"🌱 {t('analytics_avg_moisture')}",
            value=f"{avg_sm:.1f}%",
            status_type="good" if 30.0 <= avg_sm <= 60.0 else "warning",
            status_label="Balanced" if 30.0 <= avg_sm <= 60.0 else "Attention",
            description="Mean over session observations.",
            progress_fraction=avg_sm / 100,
        )

    with k2:
        avg_t = sum(p["temperature"] for p in history) / len(history) if history else (reading.temperature if reading.is_online else 0.0)
        render_metric_card(
            title=f"🌡️ {t('analytics_avg_temp')}",
            value=f"{avg_t:.1f}°C",
            status_type="good" if 15.0 <= avg_t <= 35.0 else "warning",
            status_label="Favorable" if 15.0 <= avg_t <= 35.0 else "High Heat",
            description="Mean ambient canopy temperature.",
        )

    with k3:
        uptime_pct = 100.0 if reading.is_online else 0.0
        render_metric_card(
            title=f"📡 {t('analytics_uptime')}",
            value=f"{uptime_pct:.1f}%",
            status_type="good" if reading.is_online else "alert",
            status_label="Reliable" if reading.is_online else "Offline",
            description="Field packet transmission rate.",
            progress_fraction=1.0 if reading.is_online else 0.0,
        )

    with k4:
        v_res = st.session_state.get("latest_vision_result", None)
        scan_stat = "1 Active" if v_res else "None"
        render_metric_card(
            title=f"📷 {t('analytics_scans')}",
            value=scan_stat,
            status_type="good" if (v_res and v_res.healthy) else ("warning" if v_res else "info"),
            status_label=v_res.diagnosis if v_res else "No Scans",
            description="Screening sessions in this visit.",
        )

    st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)

    # Line Charts using Streamlit native line_chart
    st.markdown(f'<div class="insights-header">📊 {t("analytics_trends_title")}</div>', unsafe_allow_html=True)
    if len(history) >= 2:
        col_ch1, col_ch2 = st.columns(2)

        with col_ch1:
            st.markdown(
                """
                <div class="weather-metric-card" style="margin-bottom: 0.5rem;">
                    <div style="font-weight: 700; font-size: 0.95rem;">🌱 Soil Moisture (%) vs. Time</div>
                    <div style="font-size: 0.82rem; color: var(--color-text-muted);">Target range: 30% (Irrigate threshold) to 60% (Saturated cutoff).</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            chart_data = {
                "Time": [p["time"] for p in history],
                "Soil Moisture (%)": [p["soil_moisture"] for p in history],
            }
            st.line_chart(chart_data, x="Time", y="Soil Moisture (%)", color="#3EA082")

        with col_ch2:
            st.markdown(
                """
                <div class="weather-metric-card" style="margin-bottom: 0.5rem;">
                    <div style="font-weight: 700; font-size: 0.95rem;">🌡️ Temperature (°C) & Humidity (%) vs. Time</div>
                    <div style="font-size: 0.82rem; color: var(--color-text-muted);">Ambient thermal and atmospheric moisture dynamics.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            chart_data_climate = {
                "Time": [p["time"] for p in history],
                "Temperature (°C)": [p["temperature"] for p in history],
                "Humidity (%)": [p["humidity"] for p in history],
            }
            st.line_chart(chart_data_climate, x="Time", y=["Temperature (°C)", "Humidity (%)"], color=["#E5684A", "#4A90E2"])
    else:
        st.info(f"💡 {t('analytics_no_history')}")

    st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)

    # Recent Farm Activity Log
    st.markdown(f'<div class="insights-header">⏱️ {t("analytics_log_title")}</div>', unsafe_allow_html=True)
    events = get_timeline_events(limit=6)
    if events:
        for evt in events:
            b_class = f"badge-{evt.severity}" if evt.severity in ("good", "warning", "alert") else "badge-info"
            st.markdown(
                f"""
                <div class="home-weather-banner" style="margin-bottom: 0.4rem; padding: 0.6rem 0.9rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px;">
                        <div>
                            <span style="font-size: 1.1rem; margin-right: 6px;">{evt.icon}</span>
                            <span style="font-weight: 700; font-size: 0.92rem;">{evt.title}</span>
                            <span style="color: var(--color-text-muted); font-size: 0.86rem; margin-left: 8px;">{evt.description}</span>
                        </div>
                        <div style="font-size: 0.82rem; color: var(--color-text-muted);">
                            🕒 {evt.timestamp}
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.info("Not enough historical data yet. As telemetry streams and events are logged, activity trends will appear here.")
