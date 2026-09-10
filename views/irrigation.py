"""Advanced Irrigation Intelligence page for KisanSense.

Provides deterministic, weather-informed irrigation recommendations,
soil moisture analysis, water-saving calculations, and hardware fail-safe visibility.
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
    # Header & Context
    # =========================================================================
    st.markdown(f'<h1 class="hero-title">💧 {t("nav_irrigation")}</h1>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="hero-tagline">Deterministic, telemetry-grounded irrigation decisions and water stewardship for {crop_title}.</p>',
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
                f'<span class="status-dot" style="background-color: var(--color-good);"></span>'
                f'<span class="status-dot-label">{t("sensor_online_label")} ({source_label}) • {t("sensor_last_updated")} {reading.last_updated}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="status-dot-row" style="justify-content: flex-end;">'
                f'<span class="status-dot" style="background-color: var(--color-alert);"></span>'
                f'<span class="status-dot-label">{t("sensor_offline_label")} ({source_label})</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Active Farm Profile summary badge
    if has_profile:
        st.markdown(
            f'<div style="margin-top: 0.4rem; margin-bottom: 0.8rem; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">'
            f'<span class="badge badge-good" style="font-size: 0.88rem; padding: 0.3rem 0.75rem;">🌾 {crop_title}</span>'
            f'<span style="color: var(--color-text-muted); font-size: 0.88rem;">🌱 Stage: {stage or "General"} • 🪨 Soil: {soil or "Loamy"} • 💧 Method: {method}</span>'
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
        state_title = "Sensor Telemetry Offline — Fail-Safe Active"
        state_desc = (
            "Automated watering decisions are suspended. Telemetry probe is unreachable. "
            "Please check probe wiring and test field soil manually before turning on irrigation."
        )
        saving_msg = "Prevented unnecessary blind pumping during telemetry outage."
    elif raw_status in FAULT_STATUSES:
        action_state = "SENSOR FAULT"
        badge_class = "badge-alert"
        state_title = f"Hardware Sensor Fault ({raw_status}) — Fail-Safe Active"
        state_desc = (
            "Field sensor reports physical hardware discontinuity or ADC error. "
            "Automated irrigation disabled to protect crop roots from waterlogging."
        )
        saving_msg = "Hardware safety latch prevented erroneous pump triggering."
    elif raw_status in ("stale_or_offline", "no_signal"):
        action_state = "STALE DATA"
        badge_class = "badge-warning"
        state_title = "Stale Telemetry — Verify Soil Moisture"
        state_desc = (
            "Telemetry data has not refreshed within expected interval. "
            "Verify sensor communications before initiating irrigation."
        )
        saving_msg = "Avoided pumping on outdated moisture readings."
    elif irrigation.needs_water:
        action_state = "WATER NOW"
        badge_class = "badge-alert"
        state_title = f"Irrigation Recommended for {crop_title}"
        state_desc = (
            f"Soil moisture ({reading.soil_moisture:.0f}%) is below the {SOIL_MOISTURE_LOW}% threshold. "
            f"Apply water via {method} to prevent crop moisture stress and root-zone drying."
        )
        saving_msg = f"Applying water promptly avoids permanent wilting in {stage or 'active'} stage."
    elif irrigation.label == "Wait / Rain Likely":
        action_state = "MONITOR"
        badge_class = "badge-warning"
        state_title = "Hold Irrigation — Rain Imminent"
        state_desc = irrigation.detail
        saving_msg = f"Holding irrigation conserves estimated 1,500–3,000L of water per acre by utilizing natural rainfall."
    elif reading.soil_moisture > SOIL_MOISTURE_HIGH:
        action_state = "NO WATER NEEDED"
        badge_class = "badge-good"
        state_title = f"Soil Saturated / Sufficiently Wet"
        state_desc = (
            f"Soil moisture ({reading.soil_moisture:.0f}%) is above {SOIL_MOISTURE_HIGH}%. "
            "Soil already contains ample moisture. No additional water needed; ensure adequate drainage."
        )
        saving_msg = "Conserving water and preventing root rot, fungus, and nutrient runoff."
    else:
        action_state = "NO WATER NEEDED"
        badge_class = "badge-good"
        state_title = f"Optimal Soil Moisture Range"
        state_desc = (
            f"Soil moisture ({reading.soil_moisture:.0f}%) is within healthy balanced bounds (30%–60%) "
            f"for {crop_title}. Continue standard monitoring."
        )
        saving_msg = "Optimal water retention maintained; zero water wasted."

    # =========================================================================
    # Prominent Irrigation Hero Banner
    # =========================================================================
    st.markdown(
        f'<div class="action-hero-card">'
        f'<div class="action-hero-header">'
        f'<div class="action-hero-title">💡 Recommended Irrigation Action</div>'
        f'<span class="badge {badge_class}">{action_state}</span>'
        f'</div>'
        f'<div class="action-headline">{state_title}</div>'
        f'<div class="action-explanation">{state_desc}</div>'
        f'<div class="action-secondary-box">💧 <strong>Water Stewardship Impact</strong>: {saving_msg}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)

    # =========================================================================
    # Telemetry Snapshot Cards
    # =========================================================================
    st.markdown(f'<div class="insights-header">📊 Live Irrigation Telemetry</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        if reading.is_online:
            sm_status = "good" if 30.0 <= reading.soil_moisture <= 60.0 else ("alert" if reading.soil_moisture < 30.0 else "warning")
            sm_label = "Optimal" if 30.0 <= reading.soil_moisture <= 60.0 else ("Low" if reading.soil_moisture < 30.0 else "High")
            render_metric_card(
                title=f"🌱 {t('card_soil_title')}",
                value=format_percent(reading.soil_moisture),
                status_type=sm_status,
                status_label=sm_label,
                description=f"Thresholds: <{SOIL_MOISTURE_LOW}% (Dry), >{SOIL_MOISTURE_HIGH}% (Wet).",
                progress_fraction=reading.soil_moisture / 100,
            )
        else:
            render_metric_card(
                title=f"🌱 {t('card_soil_title')}",
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
                title=f"🌡️ {t('card_temp_title')}",
                value=format_temperature(reading.temperature),
                status_type=t_status,
                status_label=t_label,
                description="Affects soil evaporation rate.",
            )
        else:
            render_metric_card(
                title=f"🌡️ {t('card_temp_title')}",
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
                title=f"💧 {t('card_humidity_title')}",
                value=format_percent(reading.humidity),
                status_type=h_status,
                status_label=h_label,
                description="Ambient relative humidity.",
                progress_fraction=reading.humidity / 100,
            )
        else:
            render_metric_card(
                title=f"💧 {t('card_humidity_title')}",
                value="—",
                status_type="alert",
                status_label="Offline",
                description="Sensor offline.",
            )

    with c4:
        rain_prob = getattr(weather, "precipitation_probability", 0)
        rain_status = "warning" if rain_prob >= 60 else "good"
        rain_label = "High Chance" if rain_prob >= 60 else ("Possible" if rain_prob >= 30 else "Low Chance")
        render_metric_card(
            title=f"🌧️ Rain Chance",
            value=f"{rain_prob}%",
            status_type=rain_status,
            status_label=rain_label,
            description=f"Expected: {weather.precipitation_amount_mm:.1f} mm.",
            progress_fraction=rain_prob / 100,
        )

    st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)

    # =========================================================================
    # Agronomic Soil & Crop Context Guidelines
    # =========================================================================
    col_ag1, col_ag2 = st.columns([1.5, 1])

    with col_ag1:
        st.markdown(
            f"""
            <div class="weather-impact-card">
                <div style="font-weight: 700; font-size: 1.05rem; margin-bottom: 0.5rem;">🌾 Soil & Method Agronomics</div>
                <div style="font-size: 0.92rem; line-height: 1.6; color: var(--color-text);">
                    • <strong>Soil Type ({soil or 'Loamy Soil'})</strong>: Loamy soils retain moisture effectively with balanced drainage. Maintain capillary water without saturating root air pockets.<br/>
                    • <strong>Irrigation Method ({method})</strong>: Delivers uniform moisture directly to root zones, reducing surface evaporation by up to 40% compared to flood irrigation.<br/>
                    • <strong>Growth Stage ({stage or 'Vegetative'})</strong>: Consistent moisture is crucial during flowering and fruit setting to avoid blossom drop.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_ag2:
        st.markdown(
            f"""
            <div class="weather-impact-card">
                <div style="font-weight: 700; font-size: 1.05rem; margin-bottom: 0.5rem;">🛡️ Irrigation Safety Fail-Safes</div>
                <div style="font-size: 0.88rem; line-height: 1.5; color: var(--color-text-muted);">
                    • <strong>Sensor Offline</strong>: Irrigation recommendations strictly default to FALSE.<br/>
                    • <strong>Hardware Fault</strong>: Sensor faults immediately trigger safe holding state.<br/>
                    • <strong>Plant Vision</strong>: Foliar disease screening advises cultural care but NEVER overrides water shut-off.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)

    # Assistant button
    st.button(
        "🌾 Ask KisanSense Assistant About Irrigation",
        key="btn_irrigation_ask_assistant",
        on_click=_go_to_assistant,
        args=("Should I water my crop now?",),
        use_container_width=True,
    )
