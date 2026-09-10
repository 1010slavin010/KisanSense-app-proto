"""Home page: SIH-grade Smart Farming Dashboard for KisanSense.

Answers the farmer's two most critical questions in seconds:
1. "How is my farm?" (Authoritative Farm Health status & explanation)
2. "What should I do now?" (Actionable recommendation card)

Followed by:
- 3-column Current Farm Conditions (Soil Moisture, Temperature, Air Humidity)
- Quick Farm Insights (Soil, Climate, Water, Alerts)
- "Ask KisanSense" Chatbot with interactive quick-question chips
- Collapsible Telemetry & Hardware Controls (Simulation & ESP32)
"""

from __future__ import annotations

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

    # =========================================================================
    # A. HEADER: Title, Subtitle, Connectivity & Farm Context
    # =========================================================================
    st.markdown(f'<h1 class="hero-title">🌱 {APP_NAME}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="hero-tagline">{t("home_tagline")}</p>', unsafe_allow_html=True)

    header_cols = st.columns([2, 3])
    with header_cols[0]:
        render_status_dot(t("home_status_active"))
    with header_cols[1]:
        source_tag = (
            t("sensor_source_hardware")
            if reading.source == MODE_HARDWARE
            else t("sensor_source_simulation")
        )
        if reading.is_online:
            dot_color = "var(--color-good)"
            status_text = f"{t('sensor_online_label')} ({source_tag}) • {t('sensor_last_updated')} {reading.last_updated}"
        else:
            dot_color = "var(--color-alert)"
            status_text = f"{t('sensor_offline_label')} ({source_tag})"

        st.markdown(
            f'<div class="status-dot-row" style="justify-content: flex-end;">'
            f'<span class="status-dot" style="background-color: {dot_color};"></span>'
            f'<span class="status-dot-label" style="font-size: 0.88rem;">{status_text}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Hardware diagnostics bar (if in hardware mode)
    if reading.source == MODE_HARDWARE and reading.is_online:
        batt_str = f"🔋 {reading.battery_voltage:.2f}V" if reading.battery_voltage is not None else ""
        rssi_str = f"📶 {reading.wifi_rssi} dBm" if reading.wifi_rssi is not None else ""
        dev_str = f"Node: {reading.device_id}" if reading.device_id else ""
        diag_parts = [p for p in (dev_str, batt_str, rssi_str) if p]
        if diag_parts:
            st.markdown(
                f'<div style="text-align: right; margin-top: -0.4rem; margin-bottom: 0.5rem; color: var(--color-text-muted); font-size: 0.82rem;">'
                f"{' • '.join(diag_parts)}"
                f'</div>',
                unsafe_allow_html=True,
            )

    # Active Farm Context Bar or Empty Prompt
    if has_profile:
        variety_text = f" ({profile.crop_variety})" if profile.crop_variety else ""
        location_part = f" • 📍 {profile.location}" if profile.location else ""
        stage_part = f" • 🌱 {profile.growth_stage}" if profile.growth_stage else ""
        method_part = f" • 💧 {profile.irrigation_method}" if profile.irrigation_method else ""

        st.markdown(
            f'<div style="margin-top: 0.4rem; margin-bottom: 0.8rem; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">'
            f'<span class="badge badge-good" style="font-size: 0.88rem; padding: 0.3rem 0.75rem;">🌾 {profile.crop}{variety_text}</span>'
            f'<span style="color: var(--color-text-muted); font-size: 0.9rem;">{location_part}{stage_part}{method_part}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div style="height: 0.3rem;"></div>', unsafe_allow_html=True)
        col_p1, col_p2 = st.columns([3.5, 1.2])
        with col_p1:
            st.info(f"💡 {t('home_empty_profile_prompt')}")
        with col_p2:
            if st.button(f"⚙️ {t('home_setup_profile_btn')}", key="btn_home_setup_profile", use_container_width=True):
                st.session_state.page = "farm"
                st.rerun()

    # Compute Statuses & Farm Intelligence
    weather_snap = get_weather_snapshot(
        location=profile.location if (profile and profile.location) else "Mandya, Karnataka",
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
    intel = evaluate_farm_intelligence(reading, farm_context=farm_ctx, vision_result=latest_vision)

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

    # =========================================================================
    # B. FARM HEALTH / OVERALL STATUS: "How is my farm?"
    # =========================================================================
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

    severity_dot = {
        "good": "🟢",
        "warning": "🟡",
        "alert": "🟠",
        "critical": "🔴",
    }.get(severity, "🟡")

    health_badge_class = f"badge-{severity}" if severity in ("good", "warning", "alert") else "badge-alert"

    st.markdown(
        f'<div class="farm-health-hero farm-health-hero-{severity}">'
        f'<div class="farm-health-header-row">'
        f'<div class="farm-health-title">🌾 {t("home_farm_health_title")}</div>'
        f'<span class="badge {health_badge_class} farm-health-badge">{severity_dot} {status_label_text.upper()}</span>'
        f'</div>'
        f'<div class="farm-health-summary">{intel.overall_summary}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # =========================================================================
    # C. CURRENT FARM CONDITIONS: 3-Column Telemetry Display
    # =========================================================================
    col1, col2, col3 = st.columns(3)

    # 1. Soil Moisture Card
    with col1:
        if reading.is_online:
            if reading.soil_moisture < 30.0:
                soil_desc = "Below 30% healthy threshold."
            elif reading.soil_moisture <= 60.0:
                soil_desc = "Adequate moisture for healthy roots."
            else:
                soil_desc = "Soil is sufficiently wet."

            render_metric_card(
                title=f"🌱 {t('card_soil_title')}",
                value=format_percent(reading.soil_moisture),
                status_type=soil_type,
                status_label=t(f"status_{soil_label.lower()}"),
                description=soil_desc,
                progress_fraction=reading.soil_moisture / 100,
            )
        else:
            render_metric_card(
                title=f"🌱 {t('card_soil_title')}",
                value="—",
                status_type="alert",
                status_label=t("sensor_offline_label"),
                description="Probe offline. Check connection.",
            )

    # 2. Temperature Card
    with col2:
        if reading.is_online:
            if 15.0 <= reading.temperature <= 35.0:
                temp_desc = "Comfortable range (15°C–35°C)."
            elif reading.temperature > 35.0:
                temp_desc = "High heat — watch transpiration."
            else:
                temp_desc = "Cool temperature for growth."

            render_metric_card(
                title=f"🌡️ {t('card_temp_title')}",
                value=format_temperature(reading.temperature),
                status_type=temp_type,
                status_label=t(f"status_{temp_label.lower()}"),
                description=temp_desc,
            )
        else:
            render_metric_card(
                title=f"🌡️ {t('card_temp_title')}",
                value="—",
                status_type="alert",
                status_label=t("sensor_offline_label"),
                description="Sensor offline.",
            )

    # 3. Air Humidity Card
    with col3:
        if reading.is_online:
            hum_status = "good" if 40.0 <= reading.humidity <= 75.0 else "warning"
            hum_label = "normal" if 40.0 <= reading.humidity <= 75.0 else ("high" if reading.humidity > 75.0 else "low")
            if 40.0 <= reading.humidity <= 75.0:
                hum_desc = "Balanced canopy atmospheric moisture."
            elif reading.humidity > 75.0:
                hum_desc = "High humidity — monitor foliage."
            else:
                hum_desc = "Dry air — rapid transpiration."

            render_metric_card(
                title=f"💧 {t('card_humidity_title')}",
                value=format_percent(reading.humidity),
                status_type=hum_status,
                status_label=t(f"status_{hum_label}"),
                description=hum_desc,
                progress_fraction=reading.humidity / 100,
            )
        else:
            render_metric_card(
                title=f"💧 {t('card_humidity_title')}",
                value="—",
                status_type="alert",
                status_label=t("sensor_offline_label"),
                description="Sensor offline.",
            )

    st.markdown('<div style="height: 1.25rem;"></div>', unsafe_allow_html=True)

    # =========================================================================
    # D. WHAT SHOULD I DO NOW? Prominent Action Recommendation Card
    # =========================================================================
    # Decision sourced 100% from existing Farm Intelligence & Irrigation status
    if not reading.is_online:
        action_headline = "⚠️ Inspect field sensor connection"
        action_detail = (
            "Sensor telemetry is currently offline. Verify field device power and probe contact "
            "before turning on irrigation."
        )
        action_badge_text = "SENSOR OFFLINE"
        action_badge_class = "badge-alert"
        secondary_html = ""
    elif irrigation.needs_water:
        crop_target = f" for your {profile.crop}" if has_profile and profile.crop else ""
        action_headline = f"💧 Water your crop{crop_target}"
        action_detail = (
            f"Soil moisture is at {reading.soil_moisture:.0f}%, which is below the recommended level. "
            f"Irrigation is recommended to protect crop health."
        )
        action_badge_text = "IRRIGATION RECOMMENDED"
        action_badge_class = "badge-alert"
        secondary_html = ""
    else:
        action_headline = "💧 No watering needed right now"
        action_detail = (
            f"Soil moisture is at {reading.soil_moisture:.0f}%, which is currently sufficient. "
            "Avoid adding water for now and monitor again later."
        )
        action_badge_text = "SOIL MOISTURE HEALTHY"
        action_badge_class = "badge-good"

        # Secondary advice from conditions if moisture is already fine
        secondary_note = ""
        if reading.humidity > 75.0:
            secondary_note = (
                f"👀 <strong>Foliage Monitoring</strong>: Air humidity is high ({reading.humidity:.0f}%). "
                "Keep monitoring crop foliage for prolonged wetness or signs of fungal disease."
            )
        elif reading.temperature > 35.0:
            secondary_note = (
                f"🌡️ <strong>Heat Management</strong>: Field temperature is elevated ({reading.temperature:.0f}°C). "
                "Protect sensitive plants and avoid midday spraying."
            )
        elif intel.conditions and intel.conditions[0].recommended_action:
            top_c = intel.conditions[0]
            if top_c.severity != "good":
                secondary_note = f"💡 <strong>{top_c.title}</strong>: {top_c.recommended_action}"

        secondary_html = (
            f'<div class="action-secondary-box">{secondary_note}</div>'
            if secondary_note
            else ""
        )

    st.markdown(
        f'<div class="action-hero-card">'
        f'<div class="action-hero-header">'
        f'<div class="action-hero-title">💡 {t("home_action_title")}</div>'
        f'<span class="badge {action_badge_class}">{action_badge_text}</span>'
        f'</div>'
        f'<div class="action-headline">{action_headline}</div>'
        f'<div class="action-explanation">{action_detail}</div>'
        f'{secondary_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Weather Intelligence Context Banner
    st.markdown(
        f"""
        <div class="home-weather-banner">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div>
                    <span style="font-weight: 700; font-size: 0.95rem;">🌤️ {t('weather_home_banner_title')}:</span>
                    <span style="font-size: 0.9rem; margin-left: 6px;">{weather_snap.condition} · {weather_snap.temperature_c:.0f}°C · 🌧️ {weather_snap.rain_probability}% {t('weather_rain_chance').lower()} ({weather_snap.precipitation_mm:.1f} mm)</span>
                </div>
                <div style="font-size: 0.85rem; color: var(--color-primary); font-weight: 600;">
                    📍 {weather_snap.location}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Plant Health Screening Banner (Phase 6 Vision Preview)
    if latest_vision is None:
        col_ph1, col_ph2 = st.columns([3.5, 1.2])
        with col_ph1:
            st.markdown(
                f"""
                <div class="home-weather-banner" style="margin-top: 0.5rem; margin-bottom: 0.5rem;">
                    <span style="font-weight: 700; font-size: 0.95rem;">🌿 {t('home_plant_health_title')}:</span>
                    <span style="font-size: 0.9rem; margin-left: 6px; color: var(--color-text-muted);">{t('home_plant_health_no_scan')}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_ph2:
            if st.button(f"📷 {t('home_plant_health_scan_now')}", key="btn_home_scan_leaf", use_container_width=True):
                st.session_state.page = "vision"
                st.rerun()
    else:
        conf_pct = int(round(latest_vision.confidence * 100))
        status_label = t("home_plant_health_status_healthy") if latest_vision.healthy else t("home_plant_health_status_issue")
        badge_color = "var(--color-good)" if latest_vision.healthy else "var(--color-warning)"
        urgency_txt = t(f"vision_urgency_{getattr(latest_vision, 'treatment_urgency', 'none')}")

        col_ph1, col_ph2 = st.columns([3.5, 1.2])
        with col_ph1:
            st.markdown(
                f"""
                <div class="home-weather-banner" style="margin-top: 0.5rem; margin-bottom: 0.5rem;">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                        <div>
                            <span style="font-weight: 700; font-size: 0.95rem;">🌿 {t('home_plant_health_title')}:</span>
                            <span style="font-size: 0.9rem; margin-left: 6px; font-weight: 600; color: {badge_color};">{status_label}</span>
                            <span style="font-size: 0.85rem; margin-left: 8px; color: var(--color-text);">— {latest_vision.diagnosis} ({latest_vision.crop})</span>
                        </div>
                        <div style="font-size: 0.82rem; color: var(--color-text-muted);">
                            ⚡ {t('home_plant_health_urgency')}: <strong>{urgency_txt}</strong> • 🎯 {conf_pct}%
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with col_ph2:
            if st.button(f"🔍 {t('home_plant_health_view_scan')}", key="btn_home_view_scan", use_container_width=True):
                st.session_state.page = "vision"
                st.rerun()

    # =========================================================================
    # E. QUICK FARM INSIGHTS (Soil, Climate, Water, Alerts)
    # =========================================================================
    st.markdown(f'<div class="insights-header">📋 {t("home_insights_title")}</div>', unsafe_allow_html=True)
    ins_col1, ins_col2, ins_col3, ins_col4 = st.columns(4)

    with ins_col1:
        if reading.is_online:
            if reading.soil_moisture < 30.0:
                s_txt = f"Low moisture ({reading.soil_moisture:.0f}%) — soil is dry."
            elif reading.soil_moisture <= 60.0:
                s_txt = f"Healthy moisture ({reading.soil_moisture:.0f}%) — good root uptake."
            else:
                s_txt = f"Sufficiently wet ({reading.soil_moisture:.0f}%) — avoid water."
        else:
            s_txt = "Sensor offline."
        st.markdown(
            f'<div class="insight-card">'
            f'<div class="insight-title">🌱 {t("home_soil_insight")}</div>'
            f'<div class="insight-body">{s_txt}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with ins_col2:
        if reading.is_online:
            if 15.0 <= reading.temperature <= 35.0:
                c_txt = f"Favorable temperature ({reading.temperature:.0f}°C) for growth."
            elif reading.temperature > 35.0:
                c_txt = f"Elevated heat ({reading.temperature:.0f}°C) — watch wilting."
            else:
                c_txt = f"Cool temperature ({reading.temperature:.0f}°C)."
        else:
            c_txt = "Climate sensor offline."
        st.markdown(
            f'<div class="insight-card">'
            f'<div class="insight-title">🌡️ {t("home_climate_insight")}</div>'
            f'<div class="insight-body">{c_txt}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with ins_col3:
        if reading.is_online:
            if irrigation.needs_water:
                w_txt = "Irrigation is advised for your field."
            else:
                w_txt = "Irrigation is not required now."
        else:
            w_txt = "Check soil manually."
        st.markdown(
            f'<div class="insight-card">'
            f'<div class="insight-title">💧 {t("home_water_insight")}</div>'
            f'<div class="insight-body">{w_txt}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    with ins_col4:
        if not reading.is_online:
            a_txt = "⚠️ Sensor probe is offline."
        elif reading.battery_voltage and reading.battery_voltage < 3.4:
            a_txt = f"⚠️ Battery low ({reading.battery_voltage:.2f}V)."
        elif irrigation.needs_water:
            a_txt = "⚠️ Water needed for crop."
        elif reading.humidity > 80.0:
            a_txt = "⚠️ High canopy humidity."
        else:
            a_txt = f"✅ {t('home_no_alerts')}"
        st.markdown(
            f'<div class="insight-card">'
            f'<div class="insight-title">🔔 {t("home_alerts_insight")}</div>'
            f'<div class="insight-body">{a_txt}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)

    # =========================================================================
    # E2. QUICK ACTIONS (Scan Crop, Check Irrigation, View Alerts, Devices, Analytics)
    # =========================================================================
    st.markdown('<div class="insights-header">⚡ Quick Farm Actions</div>', unsafe_allow_html=True)
    qa1, qa2, qa3, qa4, qa5, qa6 = st.columns(6)

    with qa1:
        if st.button("📷 Scan Crop", key="btn_qa_scan", use_container_width=True):
            st.session_state.page = "vision"
            st.rerun()

    with qa2:
        if st.button("💧 Irrigation", key="btn_qa_irrigation", use_container_width=True):
            st.session_state.page = "irrigation"
            st.rerun()

    with qa3:
        if st.button("🔔 View Alerts", key="btn_qa_alerts", use_container_width=True):
            st.session_state.page = "alerts"
            st.rerun()

    with qa4:
        if st.button("📡 Devices", key="btn_qa_devices", use_container_width=True):
            st.session_state.page = "devices"
            st.rerun()

    with qa5:
        if st.button("📈 Analytics", key="btn_qa_analytics", use_container_width=True):
            st.session_state.page = "analytics"
            st.rerun()

    with qa6:
        if st.button("💬 Assistant", key="btn_qa_assistant", use_container_width=True):
            st.session_state.page = "assistant"
            st.rerun()

    st.markdown('<div style="height: 1.25rem;"></div>', unsafe_allow_html=True)

    # =========================================================================
    # F. ASK KISANSENSE: Chatbot with Suggested Question Chips
    # =========================================================================
    st.markdown(
        f'<div style="margin-bottom: 0.6rem;">'
        f'<div class="assistant-title">🤖 {t("assistant_title")}</div>'
        f'<p class="assistant-subtitle">{t("home_ask_subtitle")}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Suggested question chips
    chip_cols = st.columns(4)
    chips = [
        (chip_cols[0], f"🌾 {t('home_chip_farm')}", "How is my farm?"),
        (chip_cols[1], f"💧 {t('home_chip_water')}", "Should I water my crop?"),
        (chip_cols[2], f"💡 {t('home_chip_action')}", "What should I do now?"),
        (chip_cols[3], f"🌱 {t('home_chip_soil')}", "How is the soil?"),
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
                }
                reply = get_ai_response(query, context=ctx)
                st.session_state.chat_messages.append({"role": "assistant", "content": reply})
                st.rerun()

    # Chatbot component (messages history + input)
    render_chatbot(reading=reading, farm_context=farm_ctx)

    # =========================================================================
    # G. TELEMETRY & SIMULATION CONTROLS (Collapsible)
    # =========================================================================
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
                # Hardware test injector and live listener
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
