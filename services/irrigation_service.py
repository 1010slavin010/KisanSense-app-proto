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
) -> IrrigationStatus:
    """Decide whether irrigation is needed for a given soil moisture reading.

    Preserves backward compatibility for callers passing soil_moisture only,
    while permitting crop-aware messaging and offline telemetry safety.
    """
    if not is_online:
        return IrrigationStatus(
            needs_water=False,
            label="Sensor Offline",
            detail="Soil moisture probe signal is unavailable. Please verify physical sensor connection before irrigating.",
            status_type="warning",
        )

    crop_name = ""
    if farm_context and isinstance(farm_context, dict):
        crop_name = farm_context.get("crop", "").strip()

    subject = f"{crop_name} growth" if crop_name else "crop growth"

    if soil_moisture < SOIL_MOISTURE_LOW:
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
    return IrrigationStatus(
        needs_water=False,
        label="Not Required",
        detail=f"Soil is already sufficiently wet ({soil_moisture:.0f}%).",
        status_type="warning",
    )
