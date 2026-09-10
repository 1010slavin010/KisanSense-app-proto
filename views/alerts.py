"""Alerts & Notifications page for KisanSense.

Centralizes live notifications and safety advisories across:
- Field telemetry and hardware connectivity (ESP32, battery, sensor probes)
- Soil moisture and irrigation urgency
- Weather & microclimate risk signals (heat, waterlogging, fungal-favorable conditions, wind)
- Plant vision screening advisories
"""

from __future__ import annotations

import streamlit as st

from services.farm_intelligence import evaluate_farm_intelligence
from services.farm_service import get_farm_context, get_farm_profile, is_profile_configured
from services.irrigation_service import get_irrigation_status
from services.sensor_service import get_current_sensor_data
from services.weather_intelligence import evaluate_weather_intelligence
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
    intel = evaluate_farm_intelligence(reading, farm_context=farm_ctx if has_profile else None)
    vision_result = st.session_state.get("latest_vision_result", None)

    insight = evaluate_weather_intelligence(weather, reading, farm_ctx, intel, vision_result)
    irrigation = get_irrigation_status(
        reading.soil_moisture,
        farm_context=farm_ctx,
        is_online=reading.is_online,
        raw_status=getattr(reading, "raw_status", "ok"),
        weather_context=weather,
    )

    # ---------------------------------------------------------
    # 2. Header
    # ---------------------------------------------------------
    st.markdown(
        f'<div class="weather-header-title">🔔 {t("nav_alerts")}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="weather-header-subtitle">Active alerts and safety advisories for your farm ({location} · {crop_name}).</div>',
        unsafe_allow_html=True,
    )

    # ---------------------------------------------------------
    # 3. Collect Active Alerts
    # ---------------------------------------------------------
    active_alerts: list[dict[str, str]] = []

    # Telemetry / Connectivity
    if not reading.is_online:
        active_alerts.append({
            "category": "HARDWARE",
            "title": "Sensor Probe Offline",
            "severity": "alert",
            "message": t("alert_sensor_offline"),
            "action": "Inspect the physical sensor wiring and node battery.",
        })
    elif getattr(reading, "battery_voltage", None) and reading.battery_voltage < 3.4:
        active_alerts.append({
            "category": "HARDWARE",
            "title": "Low Battery Voltage",
            "severity": "warning",
            "message": f"Telemetry node battery is at {reading.battery_voltage:.2f}V. May disconnect soon.",
            "action": "Recharge or replace the node battery.",
        })

    # Irrigation / Soil
    if reading.is_online:
        if irrigation.label == "Wait / Rain Likely":
            active_alerts.append({
                "category": "IRRIGATION",
                "title": "Hold Irrigation — Rain Likely",
                "severity": "warning",
                "message": irrigation.detail,
                "action": "Delay scheduled watering to avoid nutrient leaching and conserve water.",
            })
        elif irrigation.needs_water:
            active_alerts.append({
                "category": "IRRIGATION",
                "title": "Water Needed",
                "severity": "alert",
                "message": irrigation.detail,
                "action": "Turn on drip or furrow irrigation to restore root zone moisture.",
            })
        elif reading.soil_moisture > 70:
            active_alerts.append({
                "category": "SOIL",
                "title": "High Soil Saturation",
                "severity": "warning",
                "message": f"Soil moisture is at {reading.soil_moisture:.0f}%. High waterlogging risk.",
                "action": "Ensure drainage channels are clear to prevent root rot.",
            })

    # Weather Risk Signals
    for risk in insight.active_risks:
        active_alerts.append({
            "category": "WEATHER",
            "title": risk.risk_type.replace("_", " ").title(),
            "severity": risk.severity,
            "message": risk.description,
            "action": risk.mitigation,
        })

    # Vision screening alert
    if vision_result and not vision_result.is_healthy and vision_result.is_usable:
        active_alerts.append({
            "category": "CROP HEALTH",
            "title": f"Crop Vision: {vision_result.primary_issue}",
            "severity": "warning",
            "message": vision_result.what_was_observed,
            "action": vision_result.what_to_do,
        })

    # ---------------------------------------------------------
    # 4. Render Alerts or Empty State
    # ---------------------------------------------------------
    if not active_alerts:
        st.markdown(
            f"""
            <div class="weather-no-risks-card" style="padding: 2rem; text-align: center;">
                <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">✅</div>
                <div style="font-size: 1.15rem; font-weight: 700; color: var(--color-good);">No Active Alerts</div>
                <div style="font-size: 0.9rem; color: var(--color-text-muted); margin-top: 0.4rem;">
                    All farm sensors, soil moisture, and weather conditions are currently normal.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div style="font-size: 0.9rem; color: var(--color-text-muted); margin-bottom: 1rem;">'
            f'Found <strong>{len(active_alerts)}</strong> active notification(s) requiring attention:'
            f'</div>',
            unsafe_allow_html=True,
        )
        for alert_item in active_alerts:
            sev = alert_item["severity"]
            sev_class = f"risk-sev-{sev}"
            icon = "🚨" if sev == "alert" else ("⚠️" if sev == "warning" else "ℹ️")
            st.markdown(
                f"""
                <div class="weather-risk-banner {sev_class}">
                    <div class="weather-risk-header">
                        <span class="weather-risk-title">{icon} [{alert_item['category']}] {alert_item['title']}</span>
                        <span class="weather-risk-badge">{sev.upper()}</span>
                    </div>
                    <div class="weather-risk-desc">{alert_item['message']}</div>
                    <div class="weather-risk-mitigation"><strong>Recommended Action:</strong> {alert_item['action']}</div>
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
