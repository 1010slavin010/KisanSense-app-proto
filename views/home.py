"""Home page: Professional Smart Farming Dashboard for KisanSense.

Answers the farmer's two most critical questions in seconds:
1. "How is my farm?" (Authoritative Farm Health status & explanation)
2. "What should I do now?" (Actionable recommendation card)

Followed by:
- 4-column Live Farm Conditions (Soil Moisture, Temperature, Air Humidity, Irrigation Status)
- Crop Health screening preview
- Weather summary
- Quick Actions (Analyze Crop, Check Irrigation, View Alerts, Ask Assistant)
- "KisanSense Assistant" Chatbot with quick question chips
- Collapsible Telemetry & Hardware Controls (Simulation & ESP32)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
import streamlit as st

from components.cards import render_metric_card
from components.chatbot import render_chatbot
from components.status import render_status_dot
from services.ai_service import get_ai_response
from services.farm_intelligence import evaluate_farm_intelligence
from services.farm_service import (
    get_farm_context,
    get_farm_profile,
    is_profile_configured,
)
from services.hardware_client import HardwareClient
from services.irrigation_service import get_irrigation_status
from services.weather_service import get_weather_snapshot
from services.sensor_service import (
    ALL_CONDITIONS,
    ALL_MODES,
    CONDITION_DRY,
    CONDITION_HEAT_DROUGHT,
    CONDITION_HOT,
    CONDITION_HUMID_HEAT,
    CONDITION_NORMAL,
    CONDITION_OFFLINE,
    CONDITION_WATERLOGGING,
    CONDITION_WET,
    MODE_HARDWARE,
    MODE_SIMULATION,
    SensorReading,
    get_current_sensor_data,
    get_telemetry_mode,
)
from services.telemetry_server import (
    DEFAULT_HTTP_PORT,
    is_telemetry_server_running,
    start_telemetry_server,
)
from utils.config import APP_NAME
from utils.helpers import (
    format_percent,
    format_temperature,
    get_soil_status,
    get_temperature_status,
)
from utils.translations import t


def _get_sensor_reading(farm_ctx: dict[str, Any]) -> SensorReading:
    """Fetch or retrieve the current sensor reading from session state.

    In HARDWARE mode: Always fetches fresh telemetry from TelemetryStore on each rerun.
    In SIMULATION mode: Preserves session state for smooth time-drift stability.
    """
    mode = st.session_state.get("telemetry_mode", MODE_SIMULATION)
    cond = st.session_state.get("sim_condition", CONDITION_NORMAL)
    prev = st.session_state.get("sensor_reading")

    if mode == MODE_HARDWARE:
        st.session_state.sensor_reading = get_current_sensor_data(
            farm_context=farm_ctx, mode=mode
        )
    elif (
        prev is None
        or getattr(prev, "source", "") != mode
        or getattr(prev, "condition", None) != cond
    ):
        st.session_state.sensor_reading = get_current_sensor_data(
            farm_context=farm_ctx, condition=cond, mode=mode
        )
    return st.session_state.sensor_reading


def render() -> None:
    profile = get_farm_profile()
    farm_ctx = get_farm_context()
    has_profile = is_profile_configured(profile)
    reading = _get_sensor_reading(farm_ctx)

    # -------------------------------------------------------------------------
    # 1. HEADER: Personalized Greeting, Farm Identification & Connectivity
    # -------------------------------------------------------------------------
    farmer_display = profile.farmer_name if (has_profile and profile.farmer_name) else "Farmer"
    farm_name_display = profile.farm_name if (has_profile and profile.farm_name) else "My Farm"
    location_display = profile.location if (has_profile and profile.location) else "Mandya, Karnataka"

    col_h1, col_h2 = st.columns([3.2, 1.8])

    with col_h1:
        st.markdown(
            f'<div style="margin-bottom: 0.15rem;">'
            f'<span style="font-size: 0.95rem; font-weight: 500; color: var(--color-text-secondary);">'
            f'Welcome back, <strong>{farmer_display}</strong>'
            f'</span>'
            f'<h1 class="hero-title" style="margin-top: 0.1rem; font-size: 1.85rem;">{farm_name_display}</h1>'
            f'<div style="font-size: 0.88rem; color: var(--color-text-muted); margin-top: 0.15rem;">'
            f'📍 {location_display}'
            f'{" • 🌾 " + profile.crop if has_profile and profile.crop else ""}'
            f'{" (" + profile.crop_variety + ")" if has_profile and profile.crop_variety else ""}'
            f'{" • 🌱 " + profile.growth_stage if has_profile and profile.growth_stage else ""}'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with col_h2:
        source_tag = (
            t("sensor_source_hardware")
            if reading.source == MODE_HARDWARE
            else t("sensor_source_simulation")
        )
        if reading.is_online:
            dot_type = "good"
            status_text = f"{t('sensor_online_label')} ({source_tag})"
            timestamp_text = f"Updated {reading.last_updated or 'just now'}"
        else:
            dot_type = "alert"
            status_text = f"{t('sensor_offline_label')} ({source_tag})"
            timestamp_text = "Connection lost"

        st.markdown(
            f'<div style="display: flex; flex-direction: column; align-items: flex-end; justify-content: center; height: 100%;">'
            f'<div class="status-dot-row">'
            f'<span class="status-dot status-dot-{dot_type}"></span>'
            f'<span style="font-weight: 600; font-size: 0.88rem;">{status_text}</span>'
            f'</div>'
            f'<div style="font-size: 0.78rem; color: var(--color-text-muted); margin-top: 0.2rem;">'
            f'🕒 {timestamp_text}'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Empty Profile Setup Prompt (preserves existing test expectation)
    if not has_profile:
        st.markdown('<div style="height: 0.4rem;"></div>', unsafe_allow_html=True)
        col_p1, col_p2 = st.columns([3.5, 1.2])
        with col_p1:
            st.info(f"💡 {t('home_empty_profile_prompt')}")
        with col_p2:
            if st.button(f"⚙️ {t('home_setup_profile_btn')}", key="btn_home_setup_profile", use_container_width=True):
                st.session_state.page = "farm"
                st.rerun()

    # Fetch Weather Snapshot & Evaluate Intelligence
    weather_snap = get_weather_snapshot(
        location=location_display,
        condition_hint=st.session_state.get("sim_condition", "NORMAL"),
    )
    st.session_state.latest_weather_snapshot = weather_snap

    soil_label, soil_type = get_soil_status(reading.soil_moisture)
    temp_label, temp_type = get_temperature_status(reading.temperature)
    irrigation = get_irrigation_status(
        reading.soil_moisture,
        farm_context=farm_ctx,
        is_online=reading.is_online,
        raw_status=getattr(reading, "raw_status", "ok"),
        weather_context=weather_snap,
    )
    latest_vision = st.session_state.get("latest_vision_result")
    intel = evaluate_farm_intelligence(
        reading,
        farm_context=farm_ctx,
        vision_result=latest_vision,
        weather_context=weather_snap,
    )

    # Important Alerts Banner (prominently surfaces active alert if one exists)
    if not reading.is_online:
        st.error(f"⚠️ **{t('home_alerts_title')}**: {t('alert_sensor_offline')}")
    elif reading.battery_voltage and reading.battery_voltage < 3.4:
        st.warning(f"⚠️ **{t('home_alerts_title')}**: {t('battery_low_alert')} ({reading.battery_voltage:.2f}V)")
    elif irrigation.needs_water:
        crop_target = f" for your {profile.crop}" if has_profile and profile.crop else ""
        st.warning(
            f"⚠️ **{t('home_alerts_title')}**: {t('home_alert_water_needed')}{crop_target} "
            f"(Soil moisture is at {format_percent(reading.soil_moisture)})."
        )

    # -------------------------------------------------------------------------
    # 2. PRIMARY FARM STATUS & ACTION RECOMMENDATION ("How is my farm?")
    # -------------------------------------------------------------------------
    status_keys = {
        "Optimal Conditions": "intel_status_optimal",
        "Attention Needed": "intel_status_attention",
        "Action Recommended": "intel_status_action",
        "Action Required": "intel_status_action_required",
        "Sensor Offline": "intel_status_offline",
        "Hardware Fault Detected": "intel_status_fault",
        "Invalid Telemetry": "intel_status_fault",
        "Stale Telemetry": "intel_status_attention",
    }
    status_label_text = t(status_keys.get(intel.primary_status, "intel_status_attention"))
    severity = intel.primary_severity
    if severity not in ("good", "warning", "alert", "critical"):
        severity = "alert" if not reading.is_online else "warning"

    severity_badge_class = f"badge-{severity}" if severity in ("good", "warning", "alert") else "badge-alert"

    # Action Recommendation logic grounded in existing irrigation & farm intelligence
    if not reading.is_online:
        action_headline = "Inspect field sensor connection"
        action_detail = (
            "Sensor telemetry is currently offline. Verify power and cable contact "
            "before initiating irrigation."
        )
        action_badge_text = "SENSOR OFFLINE"
        action_badge_class = "badge-alert"
        secondary_html = ""
    elif irrigation.needs_water:
        crop_target = f" for your {profile.crop}" if has_profile and profile.crop else ""
        action_headline = f"Water your crop soon{crop_target}"
        action_detail = (
            f"Soil moisture is at {reading.soil_moisture:.0f}%, which is below the recommended threshold. "
            f"Irrigation is advised to prevent crop stress."
        )
        action_badge_text = "WATER RECOMMENDED"
        action_badge_class = "badge-alert"
        secondary_html = ""
    else:
        action_headline = "No irrigation needed right now"
        action_detail = (
            f"Soil moisture is at {reading.soil_moisture:.0f}%, which is currently sufficient. "
            "Conditions are within the monitored range; continue regular observation."
        )
        action_badge_text = "MOISTURE BALANCED"
        action_badge_class = "badge-good"

        secondary_note = ""
        if reading.humidity > 75.0:
            secondary_note = (
                f"👀 <strong>Foliage Monitoring</strong>: Air humidity is elevated ({reading.humidity:.0f}%). "
                "Keep monitoring canopy for signs of foliar dampness or fungal stress."
            )
        elif reading.temperature > 35.0:
            secondary_note = (
                f"🌡️ <strong>Heat Management</strong>: High ambient temperature ({reading.temperature:.0f}°C). "
                "Avoid midday spraying and ensure soil mulch retention."
            )
        elif intel.conditions and intel.conditions[0].recommended_action:
            top_c = intel.conditions[0]
            if top_c.severity != "good":
                secondary_note = f"💡 <strong>{top_c.title}</strong>: {top_c.recommended_action}"

        secondary_html = (
            f'<div class="action-secondary-box" style="margin-top: 0.6rem;">{secondary_note}</div>'
            if secondary_note
            else ""
        )

    # Render Two-Card Primary Status Row
    col_status, col_action = st.columns([1, 1])

    with col_status:
        st.markdown(
            f"""
            <div class="farm-health-hero farm-health-hero-{severity}" style="height: 100%;">
                <div class="farm-health-header-row">
                    <span class="farm-health-title">FARM STATUS</span>
                    <span class="badge {severity_badge_class}">● {status_label_text}</span>
                </div>
                <div style="font-size: 1.25rem; font-weight: 700; color: var(--color-text); margin-bottom: 0.35rem;">
                    {status_label_text}
                </div>
                <div class="farm-health-summary" style="font-size: 0.92rem;">
                    {intel.overall_summary}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_action:
        st.markdown(
            f"""
            <div class="action-hero-card" style="height: 100%; margin-bottom: 0;">
                <div class="action-hero-header">
                    <span class="action-hero-title">NEXT ACTION</span>
                    <span class="badge {action_badge_class}">● {action_badge_text}</span>
                </div>
                <div class="action-headline" style="font-size: 1.2rem;">
                    {action_headline}
                </div>
                <div class="action-explanation" style="font-size: 0.9rem; margin-bottom: 0;">
                    {action_detail}
                </div>
                {secondary_html}
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # 3. LIVE FARM CONDITIONS: 4 Clean Metric Cards
    # -------------------------------------------------------------------------
    st.markdown(f'<div class="insights-header">📊 Live Farm Conditions</div>', unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)

    # Card 1: Soil Moisture
    with m1:
        if reading.is_online:
            soil_desc = "Optimal root-zone moisture" if 30.0 <= reading.soil_moisture <= 60.0 else ("Dry soil — water soon" if reading.soil_moisture < 30.0 else "Wet soil — avoid water")
            render_metric_card(
                title=t("card_soil_title"),
                value=format_percent(reading.soil_moisture),
                status_type=soil_type,
                status_label=t(f"status_{soil_label.lower()}"),
                description=soil_desc,
                progress_fraction=reading.soil_moisture / 100,
            )
        else:
            render_metric_card(
                title=t("card_soil_title"),
                value="—",
                status_type="alert",
                status_label=t("sensor_offline_label"),
                description="Probe offline. Check wiring.",
            )

    # Card 2: Temperature
    with m2:
        if reading.is_online:
            t_desc = "Favorable growth range" if 15.0 <= reading.temperature <= 35.0 else ("Heatwave conditions" if reading.temperature > 35.0 else "Cool conditions")
            render_metric_card(
                title=t("card_temp_title"),
                value=format_temperature(reading.temperature),
                status_type=temp_type,
                status_label=t(f"status_{temp_label.lower()}"),
                description=t_desc,
            )
        else:
            render_metric_card(
                title=t("card_temp_title"),
                value="—",
                status_type="alert",
                status_label=t("sensor_offline_label"),
                description="Sensor offline.",
            )

    # Card 3: Air Humidity
    with m3:
        if reading.is_online:
            hum_status = "good" if 40.0 <= reading.humidity <= 75.0 else "warning"
            hum_label = "normal" if 40.0 <= reading.humidity <= 75.0 else ("high" if reading.humidity > 75.0 else "low")
            hum_desc = "Balanced canopy air" if 40.0 <= reading.humidity <= 75.0 else ("High humidity — check foliage" if reading.humidity > 75.0 else "Dry atmospheric air")
            render_metric_card(
                title=t("card_humidity_title"),
                value=format_percent(reading.humidity),
                status_type=hum_status,
                status_label=t(f"status_{hum_label}"),
                description=hum_desc,
                progress_fraction=reading.humidity / 100,
            )
        else:
            render_metric_card(
                title=t("card_humidity_title"),
                value="—",
                status_type="alert",
                status_label=t("sensor_offline_label"),
                description="Sensor offline.",
            )

    # Card 4: Irrigation Status
    with m4:
        if not reading.is_online:
            irrig_val = "Offline"
            irrig_status = "alert"
            irrig_label = "Probe Offline"
            irrig_desc = "Fail-safe engaged."
        elif irrigation.needs_water:
            irrig_val = "Water Now"
            irrig_status = "alert"
            irrig_label = "Low Moisture"
            irrig_desc = "Apply water via irrigation."
        elif irrigation.label == "Wait / Rain Likely":
            irrig_val = "Monitor"
            irrig_status = "warning"
            irrig_label = "Rain Expected"
            irrig_desc = "Hold water; rain forecasted."
        else:
            irrig_val = "Sufficient"
            irrig_status = "good"
            irrig_label = "No Water Needed"
            irrig_desc = "Moisture currently adequate."

        render_metric_card(
            title="IRRIGATION",
            value=irrig_val,
            status_type=irrig_status,
            status_label=irrig_label,
            description=irrig_desc,
        )

    st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # 4. CROP HEALTH & WEATHER (Compact 2-Column Section)
    # -------------------------------------------------------------------------
    col_crop, col_weather = st.columns([1, 1])

    # Left: Crop Health
    with col_crop:
        st.markdown(f'<div class="insights-header">🌿 Crop Health Screening</div>', unsafe_allow_html=True)
        if latest_vision is None:
            st.markdown(
                f"""
                <div class="insight-card" style="display: flex; flex-direction: column; justify-content: space-between;">
                    <div>
                        <div style="font-weight: 600; font-size: 0.95rem; color: var(--color-text); margin-bottom: 0.25rem;">
                            No crop image analyzed yet
                        </div>
                        <div style="font-size: 0.86rem; color: var(--color-text-secondary); margin-bottom: 0.75rem;">
                            Upload a photo of an affected or healthy crop leaf to screen for disease or nutrient deficiency.
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("📷 Analyze Crop", key="btn_home_scan_leaf", use_container_width=True):
                st.session_state.page = "vision"
                st.rerun()
        else:
            conf_pct = int(round(latest_vision.confidence * 100))
            badge_class = "badge-good" if latest_vision.healthy else "badge-warning"
            status_text = "Healthy Foliage" if latest_vision.healthy else "Possible Stress Detected"
            diagnosis_text = latest_vision.diagnosis

            st.markdown(
                f"""
                <div class="insight-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                        <span style="font-weight: 650; font-size: 0.95rem; color: var(--color-text);">{diagnosis_text}</span>
                        <span class="badge {badge_class}">● {status_text}</span>
                    </div>
                    <div style="font-size: 0.85rem; color: var(--color-text-secondary); margin-bottom: 0.65rem;">
                        Confidence: <strong>{conf_pct}%</strong> • Crop: <strong>{latest_vision.crop}</strong>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("🔍 View Scan Details", key="btn_home_view_scan", use_container_width=True):
                st.session_state.page = "vision"
                st.rerun()

    # Right: Weather Summary
    with col_weather:
        st.markdown(f'<div class="insights-header">🌤️ Weather & Climate</div>', unsafe_allow_html=True)
        if weather_snap is not None:
            w_cond = weather_snap.condition
            w_temp = f"{weather_snap.temperature_c:.0f}°C"
            w_rain = f"{weather_snap.rain_probability}%"
            w_wind = f"{weather_snap.wind_speed_kmh:.0f} km/h"
            w_loc = weather_snap.location

            st.markdown(
                f"""
                <div class="insight-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                        <span style="font-size: 1.15rem; font-weight: 700; color: var(--color-text);">{w_temp} · {w_cond}</span>
                        <span class="badge badge-info">📍 {w_loc}</span>
                    </div>
                    <div style="font-size: 0.88rem; color: var(--color-text-secondary); margin-bottom: 0.65rem;">
                        Rain Chance: <strong>{w_rain}</strong> • Wind: <strong>{w_wind}</strong> • Humidity: <strong>{weather_snap.humidity:.0f}%</strong>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("🌤️ View Full Weather Forecast", key="btn_home_view_weather", use_container_width=True):
                st.session_state.page = "weather"
                st.rerun()
        else:
            st.markdown(
                """
                <div class="insight-card">
                    <div style="color: var(--color-text-muted); font-size: 0.9rem;">
                        Weather data unavailable.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # 5. QUICK ACTIONS: 4 Clean Action Cards/Buttons
    # -------------------------------------------------------------------------
    st.markdown(f'<div class="insights-header">⚡ Quick Actions</div>', unsafe_allow_html=True)
    qa1, qa2, qa3, qa4 = st.columns(4)

    with qa1:
        if st.button("📷 Analyze Crop", key="btn_qa_scan", use_container_width=True):
            st.session_state.page = "vision"
            st.rerun()

    with qa2:
        if st.button("💧 Check Irrigation", key="btn_qa_irrigation", use_container_width=True):
            st.session_state.page = "irrigation"
            st.rerun()

    with qa3:
        if st.button("🔔 View Alerts", key="btn_qa_alerts", use_container_width=True):
            st.session_state.page = "alerts"
            st.rerun()

    with qa4:
        if st.button("💬 Ask Assistant", key="btn_qa_assistant", use_container_width=True):
            st.session_state.page = "assistant"
            st.rerun()

    st.markdown('<div style="height: 1.25rem;"></div>', unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # 6. KISANSENSE ASSISTANT (Chatbot on Home Page)
    # -------------------------------------------------------------------------
    with st.container(key="home_assistant_panel"):
        st.markdown(
            f'<div class="assistant-panel-header">'
            f'<div class="assistant-header-icon">🤖</div>'
            f'<div class="assistant-header-text">'
            f'<div class="assistant-title">{t("assistant_title")}</div>'
            f'<p class="assistant-subtitle">{t("assistant_subtitle")}</p>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # 4 Clean Compact Suggested Prompt Chips
        chip_cols = st.columns(4)
        chips = [
            (chip_cols[0], t("home_chip_water"), "Should I water my crop?"),
            (chip_cols[1], t("home_chip_soil"), "How is my soil?"),
            (chip_cols[2], t("home_chip_today"), "What should I do today?"),
            (chip_cols[3], t("home_chip_stress"), "Is my crop under stress?"),
        ]

        for col, label, query in chips:
            with col:
                if st.button(label, key=f"chip_home_{query[:8]}", use_container_width=True):
                    st.session_state.chat_messages.append({"role": "user", "content": query})
                    ctx = {
                        "page": "home",
                        **farm_ctx,
                        "reading": reading,
                        "soil_moisture": reading.soil_moisture,
                        "temperature": reading.temperature,
                        "humidity": reading.humidity,
                        "sensor_online": reading.is_online,
                        "last_updated": reading.last_updated,
                        "intelligence": intel,
                        "vision_result": latest_vision,
                        "weather": weather_snap,
                    }
                    reply = get_ai_response(query, context=ctx)
                    st.session_state.chat_messages.append({"role": "assistant", "content": reply})
                    st.rerun()

        # Chatbot Component inside the Assistant Panel
        render_chatbot(reading=reading, farm_context=farm_ctx, show_header=False)

    # -------------------------------------------------------------------------
    # 7. TELEMETRY & SIMULATION CONTROLS (Collapsible)
    # -------------------------------------------------------------------------
    st.markdown('<div class="section-spacer" style="height: 1.25rem;"></div>', unsafe_allow_html=True)
    with st.expander(f"⚙️ {t('sim_condition_label')}", expanded=False):
        c_mode, c_detail = st.columns([1.5, 3])

        with c_mode:
            current_mode = st.session_state.get("telemetry_mode", MODE_SIMULATION)
            mode_labels = {
                MODE_SIMULATION: t("mode_simulation"),
                MODE_HARDWARE: t("mode_hardware"),
            }

            def _on_mode_change() -> None:
                st.session_state.sensor_reading = None

            st.selectbox(
                t("telemetry_mode_label"),
                options=ALL_MODES,
                index=ALL_MODES.index(current_mode) if current_mode in ALL_MODES else 0,
                format_func=lambda m: mode_labels.get(m, m),
                key="telemetry_mode",
                on_change=_on_mode_change,
            )

        with c_detail:
            active_mode = st.session_state.get("telemetry_mode", MODE_SIMULATION)

            if active_mode == MODE_SIMULATION:
                c_sim1, c_sim2 = st.columns([3, 1])
                with c_sim1:
                    condition_labels = {
                        CONDITION_NORMAL: t("sim_normal"),
                        CONDITION_DRY: t("sim_dry"),
                        CONDITION_WET: t("sim_wet"),
                        CONDITION_HOT: t("sim_hot"),
                        CONDITION_OFFLINE: t("sim_offline"),
                        CONDITION_HEAT_DROUGHT: t("sim_heat_drought"),
                        CONDITION_WATERLOGGING: t("sim_waterlogging"),
                        CONDITION_HUMID_HEAT: t("sim_humid_heat"),
                    }
                    current_cond = st.session_state.get("sim_condition", CONDITION_NORMAL)
                    cond_idx = ALL_CONDITIONS.index(current_cond) if current_cond in ALL_CONDITIONS else 0

                    def _on_cond_change() -> None:
                        st.session_state.sensor_reading = None

                    st.selectbox(
                        "Condition",
                        options=ALL_CONDITIONS,
                        index=cond_idx,
                        format_func=lambda c: condition_labels.get(c, c),
                        key="sim_condition",
                        on_change=_on_cond_change,
                        label_visibility="collapsed",
                    )

                with c_sim2:
                    if st.button("🔄 Refresh", key="btn_refresh_sensor", use_container_width=True):
                        st.session_state.sensor_reading = get_current_sensor_data(
                            farm_context=farm_ctx,
                            condition=st.session_state.get("sim_condition", CONDITION_NORMAL),
                            previous_reading=reading,
                        )
                        st.rerun()
            else:
                if not is_telemetry_server_running():
                    try:
                        start_telemetry_server()
                    except Exception:
                        pass

                c_hw1, c_hw2 = st.columns([3, 1.2])
                with c_hw1:
                    st.caption(
                        f"📡 **ESP32 HTTP Ingestion**: Listening on `http://0.0.0.0:{DEFAULT_HTTP_PORT}/api/v1/telemetry` "
                        f"(Header: `X-Sensor-Key`)."
                    )
                with c_hw2:
                    if st.button("📡 Inject Mock ESP32", key="btn_inject_hw_mock", use_container_width=True):
                        from datetime import datetime, timezone

                        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
                        mock_pkt = {
                            "device_id": "esp32-field-01",
                            "soil_moisture": 38.5,
                            "temperature": 27.2,
                            "humidity": 64.0,
                            "battery_voltage": 3.95,
                            "wifi_rssi": -65,
                            "timestamp": now_iso,
                        }
                        HardwareClient.ingest(mock_pkt, check_timestamp_skew=False)
                        st.session_state.sensor_reading = None
                        st.rerun()
