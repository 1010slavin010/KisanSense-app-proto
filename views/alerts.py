"""Alerts & Notifications page for KisanSense.

Centralizes live notifications and safety advisories across:
- Field telemetry and hardware connectivity (ESP32, battery, sensor probes)
- Soil moisture and irrigation urgency
- Weather & microclimate risk signals (heat, waterlogging, fungal conditions, wind)
- Plant vision screening advisories
- Farm activity & advisory timeline
"""

from __future__ import annotations

import streamlit as st

from components.breadcrumbs import render_breadcrumbs
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
        weather_context=weather,
    )
    irrigation = get_irrigation_status(
        reading.soil_moisture,
        farm_context=farm_ctx,
        is_online=reading.is_online,
        raw_status=getattr(reading, "raw_status", "ok"),
        weather_context=weather,
    )

    alerts = generate_farm_alerts(
        reading=reading,
        farm_context=farm_ctx,
        intel=intel,
        weather=weather,
        vision_result=vision_result,
        irrigation_status=irrigation,
    )

    active_alerts = [a for a in alerts if a.is_active and a.severity != "GOOD"]
    active_count = len(active_alerts)

    # Header with active count
    render_breadcrumbs("Farm Alerts", "alerts")

    st.markdown(
        f'<div style="display: flex; align-items: baseline; gap: 12px; margin-bottom: 0.2rem;">'
        f'<h1 class="ks-page-title hero-title" style="margin-bottom: 0 !important;">Farm Alerts</h1>'
        f'<span class="badge badge-info" style="font-size: 0.85rem;">[{active_count} active]</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p class="hero-tagline">Safety alerts, telemetry diagnostics, and activity timeline for {crop_name} ({location}).</p>',
        unsafe_allow_html=True,
    )

    tab_alerts, tab_timeline = st.tabs(["🔔 Active Alerts", "⏱️ Farm Activity Timeline"])

    with tab_alerts:
        if not active_alerts:
            st.markdown(
                """
                <div class="weather-no-risks-card" style="padding: 1.5rem; text-align: center;">
                    <div style="font-size: 1.1rem; font-weight: 700; color: var(--color-good); margin-bottom: 0.35rem;">
                        ● No Active Alerts
                    </div>
                    <div style="font-size: 0.88rem; color: var(--color-text-secondary);">
                        All soil moisture, climate parameters, and telemetry connections are currently within monitored normal bounds.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            # Group by severity order: CRITICAL, ALERT, WARNING, INFO
            severity_groups = ["CRITICAL", "ALERT", "WARNING", "INFO"]
            for group in severity_groups:
                group_alerts = [a for a in active_alerts if a.severity.upper() == group]
                if not group_alerts:
                    continue

                dot_color = "var(--color-alert)" if group in ("CRITICAL", "ALERT") else ("var(--color-warning)" if group == "WARNING" else "var(--color-info)")
                st.markdown(
                    f'<div style="font-size: 0.85rem; font-weight: 700; color: {dot_color}; margin: 1rem 0 0.5rem 0; text-transform: uppercase; letter-spacing: 0.05em;">'
                    f'● {group}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

                for alert_item in group_alerts:
                    st.markdown(
                        f"""
                        <div class="insight-card" style="margin-bottom: 0.65rem; border-left: 4px solid {dot_color};">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 6px; margin-bottom: 0.3rem;">
                                <span style="font-size: 1rem; font-weight: 700; color: var(--color-text);">
                                    {alert_item.title}
                                </span>
                                <span style="font-size: 0.78rem; color: var(--color-text-muted);">
                                    🕒 {alert_item.timestamp}
                                </span>
                            </div>
                            <div style="font-size: 0.9rem; color: var(--color-text); line-height: 1.45; margin-bottom: 0.5rem;">
                                {alert_item.message}
                            </div>
                            <div class="action-secondary-box" style="font-size: 0.85rem;">
                                <strong>Recommended:</strong> {alert_item.recommended_action}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        col_irr, col_dev, col_ast = st.columns(3)
        with col_irr:
            if st.button("💧 Check Irrigation", key="btn_alerts_to_irrigation", use_container_width=True):
                st.session_state.page = "irrigation"
                st.rerun()
        with col_dev:
            if st.button("📡 View Devices", key="btn_alerts_to_devices", use_container_width=True):
                st.session_state.page = "devices"
                st.rerun()
        with col_ast:
            st.button(
                "💬 Ask Assistant",
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
                                <span style="font-size: 1.1rem; margin-right: 6px;">{evt.icon}</span>
                                <span style="font-weight: 700; font-size: 0.92rem; color: {sev_color};">{evt.title}</span>
                                <span style="color: var(--color-text); font-size: 0.88rem; margin-left: 6px;">— {evt.description}</span>
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
            st.info("No farm events logged yet in this session.")
