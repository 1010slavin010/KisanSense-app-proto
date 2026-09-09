"""Home page: the main KisanSense dashboard.

Shows current farm conditions (soil, temperature, air humidity, irrigation),
active farm context, sensor connectivity status, telemetry-driven alerts,
hybrid telemetry controls (Simulation vs ESP32 Hardware), and the assistant.
"""

from __future__ import annotations

import streamlit as st

from components.cards import render_metric_card
from components.chatbot import render_chatbot
from components.status import render_status_dot
from services.farm_service import (
    get_farm_context,
    get_farm_profile,
    is_profile_configured,
)
from services.hardware_client import HardwareClient
from services.irrigation_service import get_irrigation_status
from services.telemetry_server import (
    DEFAULT_HTTP_PORT,
    is_telemetry_server_running,
    start_telemetry_server,
)
from services.sensor_service import (
    ALL_CONDITIONS,
    ALL_MODES,
    CONDITION_DRY,
    CONDITION_HOT,
    CONDITION_NORMAL,
    CONDITION_OFFLINE,
    CONDITION_WET,
    MODE_HARDWARE,
    MODE_SIMULATION,
    SensorReading,
    get_current_sensor_data,
    get_telemetry_mode,
)
from utils.config import APP_NAME
from utils.helpers import (
    format_percent,
    format_temperature,
    get_soil_status,
    get_temperature_status,
)
from utils.translations import t


def _get_sensor_reading(farm_ctx: dict) -> SensorReading:
    """Fetch or retrieve the current sensor reading from session state.

    In HARDWARE mode: Always fetches fresh telemetry from TelemetryStore on each rerun
    so that newly arrived packets or staleness timeouts reflect immediately.
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

    # Header section
    st.markdown(f'<h1 class="hero-title">{APP_NAME}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="hero-tagline">{t("home_tagline")}</p>', unsafe_allow_html=True)

    header_cols = st.columns([2, 3])
    with header_cols[0]:
        render_status_dot(t("home_status_active"))
    with header_cols[1]:
        # Sensor connectivity dot & timestamp
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
            f"""
            <div class="status-dot-row" style="justify-content: flex-end;">
                <span class="status-dot" style="background-color: {dot_color};"></span>
                <span class="status-dot-label" style="font-size: 0.88rem;">{status_text}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Hardware Diagnostics Bar (if in hardware mode)
    if reading.source == MODE_HARDWARE and reading.is_online:
        batt_str = f"🔋 {reading.battery_voltage:.2f}V" if reading.battery_voltage is not None else ""
        rssi_str = f"📶 {reading.wifi_rssi} dBm" if reading.wifi_rssi is not None else ""
        dev_str = f"Node: {reading.device_id}" if reading.device_id else ""
        diag_parts = [p for p in (dev_str, batt_str, rssi_str) if p]

        if diag_parts:
            st.markdown(
                f"""
                <div style="text-align: right; margin-top: -0.5rem; margin-bottom: 0.5rem; color: var(--color-text-muted); font-size: 0.82rem;">
                    {' • '.join(diag_parts)}
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Active Farm Context Bar or Empty Prompt
    if has_profile:
        variety_text = f" ({profile.crop_variety})" if profile.crop_variety else ""
        location_part = f" • 📍 {profile.location}" if profile.location else ""
        stage_part = f" • 🌱 {profile.growth_stage}" if profile.growth_stage else ""
        method_part = f" • 💧 {profile.irrigation_method}" if profile.irrigation_method else ""

        st.markdown(
            f"""
            <div style="margin-top: 0.6rem; margin-bottom: 0.4rem; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;">
                <span class="badge badge-good" style="font-size: 0.88rem; padding: 0.3rem 0.75rem;">
                    🌾 {profile.crop}{variety_text}
                </span>
                <span style="color: var(--color-text-muted); font-size: 0.9rem;">
                    {location_part}{stage_part}{method_part}
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
        col_p1, col_p2 = st.columns([3.5, 1.2])
        with col_p1:
            st.info(f"💡 {t('home_empty_profile_prompt')}")
        with col_p2:
            if st.button(f"⚙️ {t('home_setup_profile_btn')}", key="btn_home_setup_profile", use_container_width=True):
                st.session_state.page = "farm"
                st.rerun()

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)

    # Status computation
    soil_label, soil_type = get_soil_status(reading.soil_moisture)
    temp_label, temp_type = get_temperature_status(reading.temperature)
    irrigation = get_irrigation_status(
        reading.soil_moisture,
        farm_context=farm_ctx,
        is_online=reading.is_online,
        raw_status=getattr(reading, "raw_status", "ok"),
    )

    # Important Alerts banner
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

    # Metric cards row: Soil Moisture, Temperature, Air Humidity, Irrigation
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        if reading.is_online:
            render_metric_card(
                title=t("card_soil_title"),
                value=format_percent(reading.soil_moisture),
                status_type=soil_type,
                status_label=t(f"status_{soil_label.lower()}"),
                description=t("card_soil_desc"),
                progress_fraction=reading.soil_moisture / 100,
            )
        else:
            render_metric_card(
                title=t("card_soil_title"),
                value="—",
                status_type="alert",
                status_label=t("sensor_offline_label"),
                description=t("card_soil_desc"),
            )
    with col2:
        if reading.is_online:
            render_metric_card(
                title=t("card_temp_title"),
                value=format_temperature(reading.temperature),
                status_type=temp_type,
                status_label=t(f"status_{temp_label.lower()}"),
                description=t("card_temp_desc"),
            )
        else:
            render_metric_card(
                title=t("card_temp_title"),
                value="—",
                status_type="alert",
                status_label=t("sensor_offline_label"),
                description=t("card_temp_desc"),
            )
    with col3:
        if reading.is_online:
            hum_status = "good" if 40.0 <= reading.humidity <= 75.0 else "warning"
            hum_label = "normal" if 40.0 <= reading.humidity <= 75.0 else ("high" if reading.humidity > 75.0 else "low")
            render_metric_card(
                title=t("card_humidity_title"),
                value=format_percent(reading.humidity),
                status_type=hum_status,
                status_label=t(f"status_{hum_label}"),
                description=t("card_humidity_desc"),
                progress_fraction=reading.humidity / 100,
            )
        else:
            render_metric_card(
                title=t("card_humidity_title"),
                value="—",
                status_type="alert",
                status_label=t("sensor_offline_label"),
                description=t("card_humidity_desc"),
            )
    with col4:
        render_metric_card(
            title=t("card_irrigation_title"),
            value=irrigation.label,
            status_type=irrigation.status_type,
            description=irrigation.detail,
        )

    # Telemetry and Hardware Controls
    st.markdown('<div class="section-spacer" style="height: 1.5rem;"></div>', unsafe_allow_html=True)
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

    st.markdown('<div class="section-spacer"></div>', unsafe_allow_html=True)
    render_chatbot()
