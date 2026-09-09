"""Sensor data access for KisanSense.

Acts as the single hardware boundary and abstraction layer for all sensor telemetry.
In Phase 3, delegates to the stateful SensorSimulator. When physical ESP32 devices
or MQTT/REST APIs are deployed in later phases, only this module switches to the
live hardware pipeline; callers (Home, Chatbot, Irrigation) remain untouched.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.sensor_simulator import (
    ALL_CONDITIONS,
    CONDITION_NORMAL,
    SensorSimulator,
)


@dataclass
class SensorReading:
    soil_moisture: float  # percent
    temperature: float    # Celsius
    humidity: float       # percent
    is_online: bool = True
    last_updated: str = ""
    source: str = "simulation"
    condition: str = CONDITION_NORMAL


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
) -> SensorReading:
    """Fetch current sensor reading.

    Preserves 100% backward compatibility for callers passing 0 arguments.
    """
    effective_condition = condition or _get_active_condition()
    effective_context = farm_context if farm_context is not None else _get_active_farm_context()

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
    )
