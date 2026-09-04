"""Sensor data access for KisanSense.

Phase 1 returns mock values. This module is the single integration
point for a future ESP32 / API / database data source — replace the
body of get_current_sensor_data() only; callers (e.g. the Home page)
will not need to change.
"""

from dataclasses import dataclass
import random


@dataclass
class SensorReading:
    soil_moisture: float  # percent
    temperature: float  # Celsius
    humidity: float  # percent


def get_current_sensor_data() -> SensorReading:
    """Return a simulated current sensor reading."""
    return SensorReading(
        soil_moisture=round(random.uniform(28, 65), 1),
        temperature=round(random.uniform(18, 34), 1),
        humidity=round(random.uniform(45, 80), 1),
    )
