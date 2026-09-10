"""Irrigation decision logic for KisanSense.

Maintains a deterministic decision contract based on soil moisture thresholds
while accepting optional farm context and hardware online/offline status to
protect farmers from erroneous automated watering when telemetry is down.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from utils.config import SOIL_MOISTURE_HIGH, SOIL_MOISTURE_LOW


@dataclass
class IrrigationStatus:
    needs_water: bool
    label: str
    detail: str
    status_type: str  # "good" | "warning" | "alert"


def get_irrigation_status(
    soil_moisture: float,
    farm_context: dict[str, Any] | None = None,
    is_online: bool = True,
    raw_status: str = "ok",
    weather_context: dict[str, Any] | Any | None = None,
) -> IrrigationStatus:
    """Decide whether irrigation is needed for a given soil moisture reading.

    Preserves backward compatibility for callers passing soil_moisture only,
    while permitting crop-aware messaging, offline telemetry safety, and
    weather-informed adjustments (e.g. delaying irrigation before heavy rain).
    """
    is_fault = not is_online or raw_status in (
        "probe_disconnected",
        "sensor_fault",
        "hardware_fault",
        "wire_fault",
        "adc_error",
        "fault",
    )
    if is_fault:
        fault_detail = (
            "Soil moisture probe is disconnected or reporting a hardware fault. Please verify physical wiring before irrigating."
            if raw_status == "probe_disconnected"
            else "Soil moisture probe signal is unavailable. Please verify physical sensor connection before irrigating."
        )
        return IrrigationStatus(
            needs_water=False,
            label="Sensor Offline",
            detail=fault_detail,
            status_type="warning",
        )

    crop_name = ""
    if farm_context and isinstance(farm_context, dict):
        crop_name = farm_context.get("crop", "").strip()

    subject = f"{crop_name} growth" if crop_name else "crop growth"

    # Weather-informed rain signals
    rain_prob = 0
    rain_mm = 0.0
    rain_expected = False
    if weather_context is not None:
        if isinstance(weather_context, dict):
            rain_prob = int(weather_context.get("rain_probability", 0) or 0)
            rain_mm = float(weather_context.get("precipitation_mm", 0.0) or 0.0)
            rain_expected = bool(weather_context.get("rain_expected_soon", False))
        else:
            rain_prob = int(getattr(weather_context, "rain_probability", 0) or 0)
            rain_mm = float(getattr(weather_context, "precipitation_mm", 0.0) or 0.0)
            rain_expected = bool(getattr(weather_context, "rain_expected_soon", False))
        if rain_prob >= 60 or rain_mm >= 5.0:
            rain_expected = True

    if soil_moisture < SOIL_MOISTURE_LOW:
        if rain_expected:
            return IrrigationStatus(
                needs_water=False,
                label="Wait / Rain Likely",
                detail=f"Soil moisture is low ({soil_moisture:.0f}%), but rain is expected soon ({rain_prob}% probability). Hold irrigation to conserve water and prevent waterlogging.",
                status_type="warning",
            )
        return IrrigationStatus(
            needs_water=True,
            label="Water Needed",
            detail=f"Soil moisture is low ({soil_moisture:.0f}%) for healthy {subject}.",
            status_type="alert",
        )
    if soil_moisture <= SOIL_MOISTURE_HIGH:
        return IrrigationStatus(
            needs_water=False,
            label="Not Required",
            detail=f"Soil moisture ({soil_moisture:.0f}%) is within a healthy range for {subject}.",
            status_type="good",
        )
    if rain_expected:
        return IrrigationStatus(
            needs_water=False,
            label="Not Required",
            detail=f"Soil is already sufficiently wet ({soil_moisture:.0f}%) and heavy rain is forecasted. Ensure field drainage channels are clear to prevent waterlogging.",
            status_type="warning",
        )
    return IrrigationStatus(
        needs_water=False,
        label="Not Required",
        detail=f"Soil is already sufficiently wet ({soil_moisture:.0f}%).",
        status_type="warning",
    )
