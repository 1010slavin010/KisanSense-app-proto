"""Advanced Irrigation Intelligence page for KisanSense.

Provides deterministic, weather-informed irrigation recommendations,
soil moisture analysis, water-saving calculations, and hardware fail-safe visibility.
Preserves all fail-safe and hardware interlock behavior.
"""

from __future__ import annotations

import streamlit as st

from components.cards import render_metric_card
from components.status import render_status_dot
from services.farm_service import get_farm_context, get_farm_profile, is_profile_configured
from services.hardware_client import FAULT_STATUSES
from services.irrigation_service import get_irrigation_status
from services.sensor_service import MODE_HARDWARE, get_current_sensor_data
from services.weather_service import get_weather_snapshot
from utils.config import SOIL_MOISTURE_HIGH, SOIL_MOISTURE_LOW
from utils.helpers import format_percent, format_temperature
from utils.translations import t


def _go_to_assistant(prompt: str = "") -> None:
    st.session_state.page = "assistant"
    if prompt:
        st.session_state["preset_assistant_prompt"] = prompt


def render() -> None:
    profile = get_farm_profile()
    farm_ctx = get_farm_context()
    has_profile = is_profile_configured(profile)

    sim_condition = st.session_state.get("sim_condition", "NORMAL")
    reading = get_current_sensor_data(condition=sim_condition)

    loc = profile.location if (profile and profile.location) else "Mandya, Karnataka"
    weather = get_weather_snapshot(location=loc, condition_hint=sim_condition)

    crop = profile.crop if (profile and profile.crop) else ""
    variety = profile.crop_variety if (profile and profile.crop_variety) else ""
    stage = profile.growth_stage if (profile and profile.growth_stage) else ""
    soil = profile.soil_type if (profile and profile.soil_type) else ""
    method = profile.irrigation_method if (profile and profile.irrigation_method) else "Drip Irrigation"

    crop_title = f"{crop} ({variety})" if crop and variety else (crop if crop else "General Crop")

    # Evaluate authoritative irrigation status
    irrigation = get_irrigation_status(
        reading.soil_moisture,
        farm_context=farm_ctx if has_profile else None,
        is_online=reading.is_online,
        raw_status=getattr(reading, "raw_status", "ok"),
        weather_context=weather,
    )

    # =========================================================================
    # Header & Farm Context
    # =========================================================================
    st.markdown(f'<h1 class="hero-title">💧 {t("nav_irrigation")}</h1>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="hero-tagline">Telemetry-grounded irrigation decisions and water stewardship for {crop_title}.</p>',
        unsafe_allow_html=True,
    )

    # Status row
    col_st1, col_st2 = st.columns([2, 3])
    with col_st1:
        render_status_dot(t("home_status_active"))
    with col_st2:
        source_label = (
            t("sensor_source_hardware")
            if reading.source == MODE_HARDWARE
            else t("sensor_source_simulation")
        )
        if reading.is_online:
            st.markdown(
                f'<div class="status-dot-row" style="justify-content: flex-end;">'
                f'<span class="status-dot status-dot-good"></span>'
                f'<span>{t("sensor_online_label")} ({source_label}) • {t("sensor_last_updated")} {reading.last_updated}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="status-dot-row" style="justify-content: flex-end;">'
                f'<span class="status-dot status-dot-alert"></span>'
                f'<span>{t("sensor_offline_label")} ({source_label})</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Active Farm Profile summary badge
    if has_profile:
        st.markdown(
            f'<div style="margin-top: 0.35rem; margin-bottom: 0.75rem; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">'
            f'<span class="badge badge-good">🌾 {crop_title}</span>'
            f'<span style="color: var(--color-text-secondary); font-size: 0.88rem;">🌱 Stage: {stage or "General"} • 🪨 Soil: {soil or "Loamy"} • 💧 Method: {method}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # =========================================================================
    # Irrigation State Determination
    # =========================================================================
    raw_status = (getattr(reading, "raw_status", "ok") or "ok").strip().lower()

    if not reading.is_online:
        action_state = "SENSOR OFFLINE"
        badge_class = "badge-alert"
        why_text = "Soil moisture telemetry probe is unreachable or disconnected."
        rec_text = "Automated watering decisions are suspended. Verify sensor power and probe contact before irrigating."
        saving_msg = "Fail-safe engaged: prevented unmonitored pump activation."
    elif raw_status in FAULT_STATUSES:
        action_state = "SENSOR FAULT"
        badge_class = "badge-alert"
        why_text = f"Hardware probe reports physical discontinuity or ADC error ({raw_status})."
        rec_text = "Automated irrigation disabled to protect crop roots from waterlogging. Inspect probe wiring."
        saving_msg = "Hardware safety interlock prevented erroneous pump triggering."
    elif raw_status in ("stale_or_offline", "no_signal"):
        action_state = "STALE DATA"
        badge_class = "badge-warning"
        why_text = "Telemetry packets have not refreshed within the expected observation window."
        rec_text = "Verify sensor communications and check physical soil moisture manually."
        saving_msg = "Avoided pumping decisions based on outdated moisture readings."
    elif irrigation.needs_water:
        action_state = "WATER NOW"
        badge_class = "badge-alert"
        why_text = f"Soil moisture ({reading.soil_moisture:.0f}%) is below the {SOIL_MOISTURE_LOW}% threshold."
        rec_text = f"Apply water via {method} to prevent crop moisture stress and root-zone drying."
        saving_msg = f"Timely watering prevents wilting during {stage or 'vegetative'} growth stage."
    elif irrigation.label == "Wait / Rain Likely":
        action_state = "MONITOR"
        badge_class = "badge-warning"
        why_text = irrigation.detail
        rec_text = "Hold scheduled irrigation. Natural rainfall expected to supply crop water needs."
        saving_msg = "Conserves estimated 1,500–3,000L of irrigation water per acre by leveraging rain."
    elif reading.soil_moisture > SOIL_MOISTURE_HIGH:
        action_state = "NO WATER NEEDED"
        badge_class = "badge-good"
        why_text = f"Soil moisture ({reading.soil_moisture:.0f}%) is above {SOIL_MOISTURE_HIGH}% saturation threshold."
        rec_text = "No additional water needed. Ensure adequate field drainage to protect roots."
        saving_msg = "Conserving water and preventing root rot, fungus, and nutrient leaching."
    else:
        action_state = "NO WATER NEEDED"
        badge_class = "badge-good"
        why_text = f"Soil moisture ({reading.soil_moisture:.0f}%) is within healthy balanced range (30%–60%)."
        rec_text = "Soil has adequate moisture for healthy root uptake. Continue regular observation."
        saving_msg = "Balanced water retention maintained; zero water wasted."

    # =========================================================================
    # Prominent Irrigation Status Hero Card
    # =========================================================================
    st.markdown(
        f"""
        <div class="action-hero-card">
            <div class="action-hero-header">
                <span class="action-hero-title">IRRIGATION STATUS</span>
                <span class="badge {badge_class}">● {action_state}</span>
            </div>
            <div style="margin-bottom: 0.75rem;">
                <div style="font-size: 0.85rem; font-weight: 700; color: var(--color-primary); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.2rem;">
                    WHY?
                </div>
                <div style="font-size: 1rem; color: var(--color-text); font-weight: 500; line-height: 1.45;">
                    {why_text}
                </div>
            </div>
            <div style="margin-bottom: 0.75rem;">
                <div style="font-size: 0.85rem; font-weight: 700; color: var(--color-primary); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.2rem;">
                    RECOMMENDATION
                </div>
                <div style="font-size: 0.95rem; color: var(--color-text); line-height: 1.5;">
                    {rec_text}
                </div>
            </div>
            <div class="action-secondary-box">
                💧 <strong>Water Stewardship Impact</strong>: {saving_msg}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div style="height: 0.75rem;"></div>', unsafe_allow_html=True)

    # =========================================================================
    # CURRENT CONDITIONS: 4 Metric Cards
    # =========================================================================
    st.markdown(f'<div class="insights-header">CURRENT CONDITIONS</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        if reading.is_online:
            sm_status = "good" if 30.0 <= reading.soil_moisture <= 60.0 else ("alert" if reading.soil_moisture < 30.0 else "warning")
            sm_label = "Optimal" if 30.0 <= reading.soil_moisture <= 60.0 else ("Low" if reading.soil_moisture < 30.0 else "High")
            render_metric_card(
                title=t("card_soil_title"),
                value=format_percent(reading.soil_moisture),
                status_type=sm_status,
                status_label=sm_label,
                description=f"Target: {SOIL_MOISTURE_LOW}%–{SOIL_MOISTURE_HIGH}%.",
                progress_fraction=reading.soil_moisture / 100,
            )
        else:
            render_metric_card(
                title=t("card_soil_title"),
                value="—",
                status_type="alert",
                status_label="Offline",
                description="Probe offline.",
            )

    with c2:
        if reading.is_online:
            t_status = "good" if 15.0 <= reading.temperature <= 35.0 else "warning"
            t_label = "Balanced" if 15.0 <= reading.temperature <= 35.0 else ("High Heat" if reading.temperature > 35.0 else "Cool")
            render_metric_card(
                title=t("card_temp_title"),
                value=format_temperature(reading.temperature),
                status_type=t_status,
                status_label=t_label,
                description="Soil evaporation driver.",
            )
        else:
            render_metric_card(
                title=t("card_temp_title"),
                value="—",
                status_type="alert",
                status_label="Offline",
                description="Sensor offline.",
            )

    with c3:
        if reading.is_online:
            h_status = "good" if 40.0 <= reading.humidity <= 75.0 else "warning"
            h_label = "Normal" if 40.0 <= reading.humidity <= 75.0 else ("Humid" if reading.humidity > 75.0 else "Dry Air")
            render_metric_card(
                title=t("card_humidity_title"),
                value=format_percent(reading.humidity),
                status_type=h_status,
                status_label=h_label,
                description="Ambient relative humidity.",
                progress_fraction=reading.humidity / 100,
            )
        else:
            render_metric_card(
                title=t("card_humidity_title"),
                value="—",
                status_type="alert",
                status_label="Offline",
                description="Sensor offline.",
            )

    with c4:
        rain_prob = getattr(weather, "rain_probability", 0)
        rain_status = "warning" if rain_prob >= 60 else "good"
        rain_label = "High Chance" if rain_prob >= 60 else ("Possible" if rain_prob >= 30 else "Low Chance")
        render_metric_card(
            title="RAIN STATUS",
            value=f"{rain_prob}%",
            status_type=rain_status,
            status_label=rain_label,
            description=f"{getattr(weather, 'precipitation_mm', 0.0):.1f} mm rain expected.",
        )

    st.markdown('<div style="height: 1.25rem;"></div>', unsafe_allow_html=True)

    # Ask Assistant CTA
    assistant_prompt = f"What is the recommended irrigation schedule for my {crop_title} given current soil moisture ({reading.soil_moisture:.0f}%) and weather ({getattr(weather, 'condition', 'Normal')})?"
    st.button(
        "💬 Ask Assistant About Irrigation Schedule",
        key="btn_irrigation_ask_assistant",
        on_click=_go_to_assistant,
        args=(assistant_prompt,),
        use_container_width=True,
    )
