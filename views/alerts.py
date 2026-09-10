"""Alerts & Notifications page for KisanSense.

Centralizes live notifications and safety advisories across:
- Field telemetry and hardware connectivity (ESP32, battery, sensor probes)
- Soil moisture and irrigation urgency
- Weather & microclimate risk signals (heat, waterlogging, fungal-favorable conditions, wind)
- Plant vision screening advisories
- Farm activity & advisory timeline
"""

from __future__ import annotations

import streamlit as st

from services.alert_service import generate_farm_alerts
from services.farm_intelligence import evaluate_farm_intelligence
from services.farm_service import get_farm_context, get_farm_profile, is_profile_configured
from services.irrigation_service import get_irrigation_status
from services.sensor_service import get_current_sensor_data
from services.timeline_service import get_timeline_events
from services.weather_service import get_weather_snapshot
from utils.translations import t


def _go_to_assistant(prompt: str = "") -> None:
    st.session_state.page = "assistant"
    if prompt:
        st.session_state["preset_assistant_prompt"] = prompt


def render() -> None:
    # ---------------------------------------------------------
    # 1. Fetch Farm State, Telemetry, and Weather
    # ---------------------------------------------------------
    profile = get_farm_profile()
    farm_ctx = get_farm_context()
    has_profile = is_profile_configured(profile)

    location = profile.location.strip() if (profile and profile.location and profile.location.strip()) else "Mandya, Karnataka"
    crop_name = profile.crop.strip() if (profile and profile.crop and profile.crop.strip()) else "General Crop"

    sim_condition = st.session_state.get("sim_condition", "NORMAL")
    reading = get_current_sensor_data(condition=sim_condition)

    weather = get_weather_snapshot(location=location, condition_hint=sim_condition)
    vision_result = st.session_state.get("latest_vision_result", None)
    intel = evaluate_farm_intelligence(
        reading,
        farm_context=farm_ctx if has_profile else None,
        vision_result=vision_result,
    )
    irrigation = get_irrigation_status(
        reading.soil_moisture,
        farm_context=farm_ctx,
        is_online=reading.is_online,
        raw_status=getattr(reading, "raw_status", "ok"),
        weather_context=weather,
    )

    # ---------------------------------------------------------
    # 2. Centralized Alert Generation
    # ---------------------------------------------------------
    alerts = generate_farm_alerts(
        reading=reading,
        farm_context=farm_ctx,
        intel=intel,
        weather=weather,
        vision_result=vision_result,
        irrigation_status=irrigation,
    )

    # ---------------------------------------------------------
    # 3. Header
    # ---------------------------------------------------------
    st.markdown(
        f'<div class="weather-header-title">🔔 {t("nav_alerts")}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="weather-header-subtitle">Active alerts, safety advisories, and event timeline for your farm ({location} · {crop_name}).</div>',
        unsafe_allow_html=True,
    )

    # Tabs: Active Alerts vs Event Timeline
    tab_alerts, tab_timeline = st.tabs(["🔔 Active Alerts", "⏱️ Farm Activity Timeline"])

    with tab_alerts:
        active_alerts = [a for a in alerts if a.is_active and a.severity != "GOOD"]

        if not active_alerts:
            st.markdown(
                f"""
                <div class="weather-no-risks-card" style="padding: 2rem; text-align: center;">
                    <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">✅</div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: var(--color-good);">No Active Critical or Warning Alerts</div>
                    <div style="font-size: 0.9rem; color: var(--color-text-muted); margin-top: 0.4rem;">
                        All farm sensors, soil moisture, and atmospheric conditions are currently within normal balanced limits.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div style="font-size: 0.9rem; color: var(--color-text-muted); margin-bottom: 1rem;">'
                f'Found <strong>{len(active_alerts)}</strong> active safety alert(s) requiring attention:'
                f'</div>',
                unsafe_allow_html=True,
            )
            for alert_item in active_alerts:
                sev = alert_item.severity.lower()
                sev_class = f"risk-sev-{sev}"
                icon = "🚨" if sev in ("critical", "alert") else ("⚠️" if sev == "warning" else "ℹ️")
                st.markdown(
                    f"""
                    <div class="weather-risk-banner {sev_class}">
                        <div class="weather-risk-header">
                            <span class="weather-risk-title">{icon} [{alert_item.source.upper()}] {alert_item.title}</span>
                            <span class="weather-risk-badge">{alert_item.severity}</span>
                        </div>
                        <div class="weather-risk-desc">{alert_item.message}</div>
                        <div class="weather-risk-mitigation"><strong>Recommended Action:</strong> {alert_item.recommended_action}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

        # Ask Assistant CTA
        st.button(
            "💬 Ask Assistant About Active Alerts",
            key="btn_alerts_ask_assistant",
            on_click=_go_to_assistant,
            args=("What actions should I take regarding the current farm alerts?",),
            use_container_width=True,
        )

    with tab_timeline:
        st.markdown(f'<div class="insights-header" style="margin-top: 0.5rem;">⏱️ Activity & Advisory Event Log</div>', unsafe_allow_html=True)
        events = get_timeline_events(limit=15)
        if events:
            for evt in events:
                sev_color = "var(--color-good)" if evt.severity == "good" else ("var(--color-warning)" if evt.severity == "warning" else ("var(--color-alert)" if evt.severity == "alert" else "var(--color-primary)"))
                st.markdown(
                    f"""
                    <div class="home-weather-banner" style="margin-bottom: 0.45rem; padding: 0.65rem 0.95rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                            <div>
                                <span style="font-size: 1.15rem; margin-right: 8px;">{evt.icon}</span>
                                <span style="font-weight: 700; font-size: 0.92rem; color: {sev_color};">{evt.title}</span>
                                <span style="color: var(--color-text); font-size: 0.88rem; margin-left: 8px;">— {evt.description}</span>
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
            st.info("No farm events logged yet in this session.")
