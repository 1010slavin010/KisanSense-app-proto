"""Irrigation decision logic for KisanSense.

Phase 1 uses one deterministic rule based on soil moisture alone.
Kept isolated from the UI so future phases can extend it (weather,
crop type, schedules) without touching any rendering code.
"""

from dataclasses import dataclass

from utils.config import SOIL_MOISTURE_HIGH, SOIL_MOISTURE_LOW


@dataclass
class IrrigationStatus:
    needs_water: bool
    label: str
    detail: str
    status_type: str  # "good" | "warning" | "alert"


def get_irrigation_status(soil_moisture: float) -> IrrigationStatus:
    """Decide whether irrigation is needed for a given soil moisture reading."""
    if soil_moisture < SOIL_MOISTURE_LOW:
        return IrrigationStatus(
            needs_water=True,
            label="Water Needed",
            detail="Soil moisture is low for healthy crop growth.",
            status_type="alert",
        )
    if soil_moisture <= SOIL_MOISTURE_HIGH:
        return IrrigationStatus(
            needs_water=False,
            label="Not Required",
            detail="Soil moisture is within a healthy range.",
            status_type="good",
        )
    return IrrigationStatus(
        needs_water=False,
        label="Not Required",
        detail="Soil is already sufficiently wet.",
        status_type="warning",
    )
