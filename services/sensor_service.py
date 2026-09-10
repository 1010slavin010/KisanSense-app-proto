"""Sensor data access for KisanSense.

Acts as the single hardware boundary and abstraction layer for all sensor telemetry.
Supports seamless routing between the software simulation engine (SensorSimulator)
and physical field microcontrollers (HardwareClient). Callers across the application
(Home dashboard, Chatbot, Irrigation) consume the exact same SensorReading contract.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Any

from services.hardware_client import HardwareClient
from services.sensor_simulator import (
    ALL_CONDITIONS,
    CONDITION_DRY,
    CONDITION_HEAT_DROUGHT,
    CONDITION_HOT,
    CONDITION_HUMID_HEAT,
    CONDITION_NORMAL,
    CONDITION_OFFLINE,
    CONDITION_WATERLOGGING,
    CONDITION_WET,
    SensorSimulator,
)

# Supported Telemetry Source Modes
MODE_SIMULATION = "simulation"
MODE_HARDWARE = "hardware"
ALL_MODES: list[str] = [MODE_SIMULATION, MODE_HARDWARE]


@dataclass
class SensorReading:
    soil_moisture: float  # percent
    temperature: float    # Celsius
    humidity: float       # percent
    is_online: bool = True
    last_updated: str = ""
    source: str = "simulation"
    condition: str = CONDITION_NORMAL
    device_id: str = ""
    battery_voltage: float | None = None
    wifi_rssi: int | None = None
    sensor_timestamp: str = ""
    raw_status: str = "ok"


def get_telemetry_mode() -> str:
    """Return the active telemetry mode (simulation or hardware)."""
    try:
        import streamlit as st

        if hasattr(st, "session_state") and "telemetry_mode" in st.session_state:
            val = st.session_state.telemetry_mode
            if val in ALL_MODES:
                return str(val)
    except Exception:
        pass
    return os.environ.get("KISANSENSE_TELEMETRY_MODE", MODE_SIMULATION)


def _get_active_condition() -> str:
    """Read simulation condition from Streamlit session state if available."""
    try:
        import streamlit as st

        if hasattr(st, "session_state") and "sim_condition" in st.session_state:
            val = st.session_state.sim_condition
            if val in ALL_CONDITIONS:
                return str(val)
    except Exception:
        pass
    return CONDITION_NORMAL


def _get_active_farm_context() -> dict[str, Any]:
    """Read farm context from farm_service if available."""
    try:
        from services.farm_service import get_farm_context

        return get_farm_context()
    except Exception:
        return {}


def get_current_sensor_data(
    farm_context: dict[str, Any] | None = None,
    condition: str | None = None,
    previous_reading: SensorReading | None = None,
    device_id: str | None = None,
    mode: str | None = None,
) -> SensorReading:
    """Fetch current sensor reading from the active telemetry source.

    Preserves 100% backward compatibility for callers passing zero arguments.
    """
    effective_mode = mode or get_telemetry_mode()

    if effective_mode == MODE_HARDWARE:
        raw = HardwareClient.get_reading(device_id=device_id)
    else:
        effective_condition = condition or _get_active_condition()
        effective_context = (
            farm_context if farm_context is not None else _get_active_farm_context()
        )
        raw = SensorSimulator.generate_reading(
            condition=effective_condition,
            farm_context=effective_context,
            previous_reading=previous_reading,
        )

    return SensorReading(
        soil_moisture=raw["soil_moisture"],
        temperature=raw["temperature"],
        humidity=raw["humidity"],
        is_online=raw["is_online"],
        last_updated=raw["last_updated"],
        source=raw["source"],
        condition=raw["condition"],
        device_id=raw.get("device_id", ""),
        battery_voltage=raw.get("battery_voltage"),
        wifi_rssi=raw.get("wifi_rssi"),
        sensor_timestamp=raw.get("sensor_timestamp", ""),
        raw_status=raw.get("raw_status", "ok"),
    )
