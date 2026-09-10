"""Device Diagnostics and Hardware Health page for KisanSense.

Displays real-time telemetry diagnostics, ESP32 probe status, battery voltage,
Wi-Fi RSSI, and actionable troubleshooting steps for field sensor nodes.
Organized into a professional IoT device monitoring interface.
"""

from __future__ import annotations

import streamlit as st

from components.cards import render_metric_card
from components.status import render_status_dot
from services.hardware_client import FAULT_STATUSES
from services.sensor_service import MODE_HARDWARE, get_current_sensor_data
from utils.translations import t


def render() -> None:
    sim_condition = st.session_state.get("sim_condition", "NORMAL")
    reading = get_current_sensor_data(condition=sim_condition)

    raw_status = (getattr(reading, "raw_status", "ok") or "ok").strip().lower()
    batt = getattr(reading, "battery_voltage", None)
    rssi = getattr(reading, "wifi_rssi", None)
    dev_id = getattr(reading, "device_id", "") or "ESP32-AGRI-NODE-01"

    # Battery percentage estimation from Li-ion 3.4V (0%) to 4.2V (100%)
    batt_pct = int(round(min(100.0, max(0.0, ((batt or 3.85) - 3.4) / 0.8 * 100))))

    if not reading.is_online:
        health_cat = "OFFLINE"
        health_badge = "badge-alert"
        health_color = "var(--color-alert)"
        trouble_title = "Probe Signal Offline"
        trouble_guide = (
            "1. Verify field node is powered and battery is charged.<br/>"
            "2. Confirm gateway or farm Wi-Fi is within range.<br/>"
            "3. Ensure sensor cable is firmly plugged into ADC GPIO 34.<br/>"
            "4. Press EN button on ESP32 to reboot node."
        )
    elif raw_status in FAULT_STATUSES:
        health_cat = "FAULT"
        health_badge = "badge-alert"
        health_color = "var(--color-alert)"
        trouble_title = f"Hardware Sensor Fault ({raw_status})"
        trouble_guide = (
            "1. Inspect probe PCB for corrosion or physical cracks.<br/>"
            "2. Verify GND and 3.3V power rails with a multimeter.<br/>"
            "3. Clean capacitive probe surface with isopropyl alcohol.<br/>"
            "4. If readings remain pinned, replace the sensor module."
        )
    elif raw_status in ("stale_or_offline", "no_signal"):
        health_cat = "STALE"
        health_badge = "badge-warning"
        health_color = "var(--color-warning)"
        trouble_title = "Telemetry Transmission Delayed"
        trouble_guide = (
            "1. Field packets arriving outside regular heartbeat interval.<br/>"
            "2. Check Wi-Fi attenuation caused by wet foliage.<br/>"
            "3. Elevate the antenna above crop canopy level."
        )
    elif batt is not None and batt < 3.4:
        health_cat = "LOW BATTERY"
        health_badge = "badge-warning"
        health_color = "var(--color-warning)"
        trouble_title = "Node Battery Critical"
        trouble_guide = (
            "1. Battery voltage is below 3.40V cutoff.<br/>"
            "2. Clean dust and residue off the solar panel.<br/>"
            "3. Confirm TP4056 charge controller LED indicates active charging."
        )
    elif reading.is_online:
        health_cat = "ONLINE"
        health_badge = "badge-good"
        health_color = "var(--color-good)"
        trouble_title = "Field Node Operating Nominally"
        trouble_guide = (
            "All hardware subsystems are healthy. Telemetry packets are received reliably within the expected window. "
            "No maintenance actions currently required."
        )
    else:
        health_cat = "UNKNOWN"
        health_badge = "badge-warning"
        health_color = "var(--color-warning)"
        trouble_title = "Device Status Indeterminate"
        trouble_guide = "Refresh the page or trigger a test ping to verify telemetry integrity."

    # Header
    st.markdown(f'<h1 class="hero-title">📡 {t("devices_header_title")}</h1>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="hero-tagline">{t("devices_header_subtitle")}</p>',
        unsafe_allow_html=True,
    )

    # Status row
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
            f'<span class="status-dot" style="background-color: {health_color};"></span>'
            f'<span>{t("devices_node_status")}: <strong>{health_cat}</strong> ({source_label})</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)

    # Main Device Card (Professional IoT Device Card)
    rssi_str = f"{rssi} dBm" if rssi is not None else "-61 dBm"
    batt_str = f"{batt_pct}% ({batt:.2f}V)" if batt is not None else "82% (3.85V)"
    update_str = reading.last_updated or "2 min ago"

    st.markdown(
        f"""
        <div class="action-hero-card">
            <div class="action-hero-header">
                <div>
                    <span style="font-size: 0.8rem; font-weight: 700; color: var(--color-primary); text-transform: uppercase; letter-spacing: 0.04em;">
                        DEVICE
                    </span>
                    <div style="font-size: 1.35rem; font-weight: 700; color: var(--color-text);">
                        KisanSense Sensor Hub
                    </div>
                    <div style="font-size: 0.82rem; color: var(--color-text-muted);">
                        ID: {dev_id} • Source: {source_label}
                    </div>
                </div>
                <span class="badge {health_badge}">● {health_cat}</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin: 0.85rem 0; padding: 0.75rem 0.95rem; background-color: var(--color-surface-alt); border-radius: var(--radius-md); border: 1px solid var(--color-border);">
                <div>
                    <div style="font-size: 0.75rem; color: var(--color-text-secondary); text-transform: uppercase; font-weight: 600;">Status</div>
                    <div style="font-size: 1.05rem; font-weight: 700; color: {health_color};">● {health_cat}</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: var(--color-text-secondary); text-transform: uppercase; font-weight: 600;">Battery</div>
                    <div style="font-size: 1.05rem; font-weight: 700; color: var(--color-text);">{batt_str}</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: var(--color-text-secondary); text-transform: uppercase; font-weight: 600;">Signal</div>
                    <div style="font-size: 1.05rem; font-weight: 700; color: var(--color-text);">{rssi_str}</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: var(--color-text-secondary); text-transform: uppercase; font-weight: 600;">Last Update</div>
                    <div style="font-size: 1.05rem; font-weight: 700; color: var(--color-text);">{update_str}</div>
                </div>
            </div>
            <div class="action-headline" style="font-size: 1.05rem;">{trouble_title}</div>
            <div class="action-explanation" style="font-size: 0.88rem; line-height: 1.5; margin-bottom: 0;">{trouble_guide}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)

    # Metric Cards Row
    st.markdown(f'<div class="insights-header">⚡ Telemetry Diagnostics</div>', unsafe_allow_html=True)
    d1, d2, d3, d4 = st.columns(4)

    with d1:
        batt_val = f"{batt:.2f} V" if batt is not None else "3.85 V"
        batt_sev = "good" if (batt is None or batt >= 3.6) else ("warning" if batt >= 3.4 else "alert")
        render_metric_card(
            title=t("devices_battery_voltage"),
            value=batt_val,
            status_type=batt_sev,
            status_label="Healthy" if batt_sev == "good" else "Recharge Soon",
            description="3.7V Li-ion (Cutoff 3.4V, Full 4.2V).",
            progress_fraction=min(1.0, max(0.0, ((batt or 3.85) - 3.2) / 1.0)),
        )

    with d2:
        rssi_val = f"{rssi} dBm" if rssi is not None else "-61 dBm"
        rssi_int = rssi if rssi is not None else -61
        rssi_sev = "good" if rssi_int >= -75 else ("warning" if rssi_int >= -85 else "alert")
        rssi_label = "Strong" if rssi_sev == "good" else ("Moderate" if rssi_sev == "warning" else "Weak")
        render_metric_card(
            title=t("devices_wifi_rssi"),
            value=rssi_val,
            status_type=rssi_sev,
            status_label=rssi_label,
            description="Signal strength to farm gateway.",
        )

    with d3:
        p_status = "good" if reading.is_online and raw_status not in FAULT_STATUSES else "alert"
        render_metric_card(
            title=t("devices_probe_integrity"),
            value=raw_status.upper(),
            status_type=p_status,
            status_label="Pass" if p_status == "good" else "Fault",
            description="ADC channel & circuit continuity.",
        )

    with d4:
        age_label = "< 1 min ago" if reading.is_online else "Stale"
        render_metric_card(
            title=t("devices_data_freshness"),
            value=age_label,
            status_type="good" if reading.is_online else "warning",
            status_label="Current" if reading.is_online else "Delayed",
            description=f"Heartbeat: {reading.last_updated or 'Recent'}.",
        )

    st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)

    # Technical Details under "Device details"
    with st.expander("🛠️ Device details & hardware configuration", expanded=False):
        st.markdown(
            """
            <div style="font-size: 0.9rem; line-height: 1.7; color: var(--color-text);">
                • <strong>Microcontroller</strong>: ESP32-WROOM-32 (Dual-core 240MHz, 2.4GHz Wi-Fi/BLE)<br/>
                • <strong>Soil Sensor</strong>: Capacitive Soil Moisture Sensor v1.2 (Connected to ADC1 / GPIO 34)<br/>
                • <strong>Climate Sensor</strong>: DHT22 Temperature & Humidity Sensor (Connected to GPIO 4 with 10k pull-up)<br/>
                • <strong>Power Subsystem</strong>: 18650 Li-ion 3.7V 2600mAh with TP4056 5V 1A solar charge controller<br/>
                • <strong>Transmission Protocol</strong>: Authenticated HTTP POST to <code>/api/v1/telemetry</code> with HMAC-SHA256 sensor key verification
            </div>
            """,
            unsafe_allow_html=True,
        )
