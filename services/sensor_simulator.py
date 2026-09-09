"""Software sensor simulator for KisanSense.

Generates realistic, stateful agricultural telemetry for soil moisture,
temperature, and air humidity. Supports distinct environmental and hardware
conditions (NORMAL, DRY, WET, HOT, SENSOR_OFFLINE) and adjusts telemetry
based on farm context (soil type, crop growth stage).
"""

from __future__ import annotations

from datetime import datetime
import random
from typing import Any

# Supported simulation condition profiles
CONDITION_NORMAL = "NORMAL"
CONDITION_DRY = "DRY"
CONDITION_WET = "WET"
CONDITION_HOT = "HOT"
CONDITION_OFFLINE = "SENSOR_OFFLINE"

ALL_CONDITIONS: list[str] = [
    CONDITION_NORMAL,
    CONDITION_DRY,
    CONDITION_WET,
    CONDITION_HOT,
    CONDITION_OFFLINE,
]

# Baseline profile targets: (soil_moisture, temperature, humidity)
PROFILE_BASELINES: dict[str, dict[str, float]] = {
    CONDITION_NORMAL: {"soil_moisture": 45.0, "temperature": 26.5, "humidity": 62.0},
    CONDITION_DRY: {"soil_moisture": 21.5, "temperature": 33.5, "humidity": 38.0},
    CONDITION_WET: {"soil_moisture": 72.0, "temperature": 22.0, "humidity": 82.0},
    CONDITION_HOT: {"soil_moisture": 29.0, "temperature": 39.0, "humidity": 28.0},
    CONDITION_OFFLINE: {"soil_moisture": 0.0, "temperature": 0.0, "humidity": 0.0},
}

# Agronomic physical retention offsets
SOIL_MOISTURE_OFFSETS: dict[str, float] = {
    "Sandy Soil": -3.5,        # Drains rapidly
    "Clay Soil": 3.0,          # High water retention
    "Loamy Soil": 0.0,         # Balanced
    "Black / Regur Soil": 2.5, # Rich clay content
    "Red Soil": -1.5,          # Porous, moderate drainage
    "Alluvial Soil": 0.5,      # Fertile, good retention
    "Silt Soil": 1.0,          # Fine particles, slow drainage
}

# Crop growth stage transpiration offsets
STAGE_TRANSPIRATION_OFFSETS: dict[str, float] = {
    "Sowing / Germination": 1.5,
    "Vegetative Growth": 0.0,
    "Flowering": -2.0,             # Peak water requirement
    "Fruiting / Pod Formation": -2.5, # Heavy transpiration
    "Harvesting / Mature": 1.0,     # Reduced water uptake
}


class SensorSimulator:
    """Stateful generator of realistic agricultural telemetry."""

    @staticmethod
    def generate_reading(
        condition: str = CONDITION_NORMAL,
        farm_context: dict[str, Any] | None = None,
        previous_reading: Any | None = None,
    ) -> dict[str, Any]:
        """Generate a simulated sensor reading dict.

        Args:
            condition: ONE of ALL_CONDITIONS
            farm_context: Optional farm profile dict (soil_type, growth_stage, etc.)
            previous_reading: Optional existing reading to allow smooth drift
        """
        now_str = datetime.now().strftime("%H:%M:%S")

        if condition == CONDITION_OFFLINE:
            return {
                "soil_moisture": 0.0,
                "temperature": 0.0,
                "humidity": 0.0,
                "is_online": False,
                "last_updated": now_str,
                "source": "simulation",
                "condition": CONDITION_OFFLINE,
            }

        base = PROFILE_BASELINES.get(condition, PROFILE_BASELINES[CONDITION_NORMAL])
        soil_moisture = base["soil_moisture"]
        temperature = base["temperature"]
        humidity = base["humidity"]

        # Apply farm-context physical adjustments
        ctx = farm_context or {}
        soil_type = ctx.get("soil_type", "")
        if soil_type in SOIL_MOISTURE_OFFSETS:
            soil_moisture += SOIL_MOISTURE_OFFSETS[soil_type]

        growth_stage = ctx.get("growth_stage", "")
        if growth_stage in STAGE_TRANSPIRATION_OFFSETS:
            soil_moisture += STAGE_TRANSPIRATION_OFFSETS[growth_stage]

        # Apply smooth time-drift if continuing an existing condition
        if previous_reading and getattr(previous_reading, "condition", None) == condition and getattr(previous_reading, "is_online", True):
            # Gentle drift (±0.3% moisture, ±0.2°C temp, ±0.4% humidity)
            d_moist = random.uniform(-0.3, 0.3)
            d_temp = random.uniform(-0.2, 0.2)
            d_hum = random.uniform(-0.4, 0.4)

            # Re-anchor slightly towards target baseline
            prev_m = getattr(previous_reading, "soil_moisture", soil_moisture)
            prev_t = getattr(previous_reading, "temperature", temperature)
            prev_h = getattr(previous_reading, "humidity", humidity)

            soil_moisture = round(prev_m * 0.85 + (soil_moisture + d_moist) * 0.15, 1)
            temperature = round(prev_t * 0.85 + (temperature + d_temp) * 0.15, 1)
            humidity = round(prev_h * 0.85 + (humidity + d_hum) * 0.15, 1)
        else:
            # Initial sampling around profile target with minor micro-jitter
            soil_moisture = round(soil_moisture + random.uniform(-0.5, 0.5), 1)
            temperature = round(temperature + random.uniform(-0.4, 0.4), 1)
            humidity = round(humidity + random.uniform(-0.6, 0.6), 1)

        # Physical clamping
        soil_moisture = max(5.0, min(95.0, soil_moisture))
        temperature = max(5.0, min(55.0, temperature))
        humidity = max(10.0, min(100.0, humidity))

        return {
            "soil_moisture": soil_moisture,
            "temperature": temperature,
            "humidity": humidity,
            "is_online": True,
            "last_updated": now_str,
            "source": "simulation",
            "condition": condition,
        }
