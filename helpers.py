"""Small, pure helper functions shared across pages and components."""

from __future__ import annotations

from utils.config import (
    SOIL_MOISTURE_HIGH,
    SOIL_MOISTURE_LOW,
    TEMP_NORMAL_MAX,
    TEMP_NORMAL_MIN,
)


def get_soil_status(soil_moisture: float) -> tuple[str, str]:
    """Return (label, status_type) for a soil moisture reading."""
    if soil_moisture < SOIL_MOISTURE_LOW:
        return "Low", "alert"
    if soil_moisture <= SOIL_MOISTURE_HIGH:
        return "Good", "good"
    return "Wet", "warning"


def get_temperature_status(temperature: float) -> tuple[str, str]:
    """Return (label, status_type) for a temperature reading."""
    if temperature < TEMP_NORMAL_MIN:
        return "Low", "warning"
    if temperature <= TEMP_NORMAL_MAX:
        return "Normal", "good"
    return "High", "alert"


def format_percent(value: float) -> str:
    return f"{value:.0f}%"


def format_temperature(value: float) -> str:
    return f"{value:.0f}°C"
