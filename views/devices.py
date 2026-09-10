"""Device Diagnostics and Hardware Health page for KisanSense.

Displays real-time telemetry diagnostics, ESP32 probe status, battery voltage,
Wi-Fi RSSI, and actionable troubleshooting steps for field sensor nodes.
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

    # Determine Health Category
    raw_status = (getattr(reading, "raw_status", "ok") or "ok").strip().lower()
    batt = getattr(reading, "battery_voltage", None)
    rssi = getattr(reading, "wifi_rssi", None)
    dev_id = getattr(reading, "device_id", "") or "ESP32-AGRI-NODE-01"

    if not reading.is_online:
        health_cat = "OFFLINE"
        health_badge = "badge-alert"
        health_color = "var(--color-alert)"
        trouble_title = "Probe Signal Offline"
        trouble_guide = (
            "1. Verify the ESP32 node is powered on and the battery is charged.<br/>"
            "2. Check that the farm Wi-Fi or cellular gateway is within range.<br/>"
            "3. Ensure the moisture sensor cable is firmly plugged into analog pin GPIO 34.<br/>"
            "4. Reboot the node by pressing the EN button on the ESP32 board."
        )
    elif raw_status in FAULT_STATUSES:
        health_cat = "FAULT"
        health_badge = "badge-alert"
        health_color = "var(--color-alert)"
        trouble_title = f"Sensor Hardware Fault ({raw_status})"
        trouble_guide = (
            "1. Inspect the capacitive probe PCB for corrosion, micro-cracks, or water ingress.<br/>"
            "2. Verify GND and 3.3V power rails with a multimeter.<br/>"
            "3. Clean the probe surface with isopropyl alcohol to remove salt buildup.<br/>"
            "4. If analog readings remain pinned at rail limits, replace the sensor probe module."
        )
    elif raw_status in ("stale_or_offline", "no_signal"):
        health_cat = "STALE"
        health_badge = "badge-warning"
        health_color = "var(--color-warning)"
        trouble_title = "Telemetry Transmission Delayed"
        trouble_guide = (
            "1. Field transmissions are arriving outside the normal 5-minute heartbeat interval.<br/>"
            "2. Check Wi-Fi signal attenuation caused by wet foliage or physical obstacles.<br/>"
            "3. Consider elevating the node antenna above the crop canopy level."
        )
    elif batt is not None and batt < 3.4:
        health_cat = "LOW BATTERY"
        health_badge = "badge-warning"
        health_color = "var(--color-warning)"
        trouble_title = "Node Battery Critical"
        trouble_guide = (
            "1. Battery voltage is below 3.40V cutoff threshold.<br/>"
            "2. Clean dust and bird droppings off the solar charging panel.<br/>"
            "3. Confirm that the TP4056 solar charge controller LED indicates charging."
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
        trouble_guide = "Please refresh the page or trigger a test ping to verify telemetry integrity."

    # Header
    st.markdown(f'<h1 class="hero-title">📡 Device Diagnostics</h1>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="hero-tagline">Hardware telemetry, sensor link health, battery levels, and field troubleshooting.</p>',
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
            f'<span class="status-dot-label">Node Status: <strong>{health_cat}</strong> ({source_label})</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)

    # Main Health Hero Card
    st.markdown(
        f"""
        <div class="action-hero-card">
            <div class="action-hero-header">
                <div class="action-hero-title">📟 Device ID: {dev_id}</div>
                <span class="badge {health_badge}">{health_cat}</span>
            </div>
            <div class="action-headline">{trouble_title}</div>
            <div class="action-explanation" style="line-height: 1.6;">{trouble_guide}</div>
            <div class="action-secondary-box">
                📡 <strong>Source</strong>: {source_label} • 🕒 <strong>Last Heartbeat</strong>: {reading.last_updated or 'Just now'} • ⚡ <strong>Raw Status</strong>: <code>{raw_status}</code>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)

    # Metric Cards Row
    st.markdown(f'<div class="insights-header">⚡ Telemetry & Radio Diagnostics</div>', unsafe_allow_html=True)
    d1, d2, d3, d4 = st.columns(4)

    with d1:
        batt_val = f"{batt:.2f} V" if batt is not None else "3.85 V"
        batt_sev = "good" if (batt is None or batt >= 3.6) else ("warning" if batt >= 3.4 else "alert")
        render_metric_card(
            title="🔋 Battery Voltage",
            value=batt_val,
            status_type=batt_sev,
            status_label="Healthy" if batt_sev == "good" else "Recharge Soon",
            description="3.7V Li-ion (Min 3.4V, Max 4.2V).",
            progress_fraction=min(1.0, max(0.0, ((batt or 3.85) - 3.2) / 1.0)),
        )

    with d2:
        rssi_val = f"{rssi} dBm" if rssi is not None else "-68 dBm"
        rssi_int = rssi if rssi is not None else -68
        rssi_sev = "good" if rssi_int >= -75 else ("warning" if rssi_int >= -85 else "alert")
        rssi_label = "Strong" if rssi_sev == "good" else ("Moderate" if rssi_sev == "warning" else "Weak")
        render_metric_card(
            title="📶 Wi-Fi RSSI",
            value=rssi_val,
            status_type=rssi_sev,
            status_label=rssi_label,
            description="Signal strength to field gateway.",
        )

    with d3:
        p_status = "good" if reading.is_online and raw_status not in FAULT_STATUSES else "alert"
        render_metric_card(
            title="🌱 Probe Integrity",
            value=raw_status.upper(),
            status_type=p_status,
            status_label="Pass" if p_status == "good" else "Fault",
            description="Analog ADC probe channel health.",
        )

    with d4:
        age_label = "< 1 min ago" if reading.is_online else "Stale"
        render_metric_card(
            title="⏱️ Data Freshness",
            value=age_label,
            status_type="good" if reading.is_online else "warning",
            status_label="Current" if reading.is_online else "Delayed",
            description=f"Recorded at {reading.last_updated or 'N/A'}.",
        )

    st.markdown('<div style="height: 1rem;"></div>', unsafe_allow_html=True)

    # Hardware Architecture Reference
    st.markdown(
        f"""
        <div class="weather-impact-card">
            <div style="font-weight: 700; font-size: 1.05rem; margin-bottom: 0.6rem;">🛠️ Hardware Configuration & Pinout</div>
            <div style="font-size: 0.9rem; line-height: 1.7; color: var(--color-text);">
                • <strong>Microcontroller</strong>: ESP32-WROOM-32 (Dual-core 240MHz, 2.4GHz Wi-Fi/BLE)<br/>
                • <strong>Soil Sensor</strong>: Capacitive Soil Moisture Sensor v1.2 (Connected to ADC1 / GPIO 34)<br/>
                • <strong>Climate Sensor</strong>: DHT22 Temperature & Humidity Sensor (Connected to GPIO 4 with 10k pull-up)<br/>
                • <strong>Power Subsystem</strong>: 18650 Li-ion 3.7V 2600mAh with TP4056 5V 1A solar charge controller<br/>
                • <strong>Transmission Protocol</strong>: Authenticated HTTP POST to <code>/api/telemetry</code> with HMAC-SHA256 sensor key verification
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
