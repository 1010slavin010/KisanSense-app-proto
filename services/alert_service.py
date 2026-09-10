"""Centralized Alert System and Safety Advisory Service for KisanSense.

Evaluates multi-sensor telemetry, hardware health, weather risks, plant vision screening,
and farm intelligence to produce unified, deterministic, and non-alarmist agricultural alerts.
Shared by Home, Alerts, and Chatbot to prevent conflicting recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from services.hardware_client import FAULT_STATUSES
from services.irrigation_service import IrrigationStatus
from services.sensor_service import SensorReading


# Severity ranking
SEVERITY_ORDER: dict[str, int] = {
    "CRITICAL": 50,
    "ALERT": 40,
    "WARNING": 30,
    "INFO": 20,
    "GOOD": 10,
}


@dataclass
class FarmAlert:
    """Represents a unified, structured farm alert or safety advisory."""

    id: str
    severity: str  # "CRITICAL" | "ALERT" | "WARNING" | "INFO" | "GOOD"
    title: str
    message: str
    source: str  # "hardware" | "sensor" | "irrigation" | "weather" | "vision" | "farm_intelligence"
    timestamp: str
    is_active: bool
    recommended_action: str

    @property
    def severity_weight(self) -> int:
        return SEVERITY_ORDER.get(self.severity.upper(), 0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "source": self.source,
            "timestamp": self.timestamp,
            "is_active": self.is_active,
            "recommended_action": self.recommended_action,
        }


def generate_farm_alerts(
    reading: SensorReading | None,
    farm_context: dict[str, Any] | None = None,
    intel: Any | None = None,
    weather: Any | None = None,
    vision_result: Any | None = None,
    irrigation_status: IrrigationStatus | None = None,
) -> list[FarmAlert]:
    """Generate authoritative, centralized farm alerts from all active subsystems.

    Never uses alarming medical claims or guarantees. All advice uses conservative
    scientific and cultural guidance.
    """
    alerts: list[FarmAlert] = []
    now_str = datetime.now().strftime("%I:%M %p")
    ctx = farm_context or {}
    crop = ctx.get("crop", "").strip()
    crop_name = f"for your {crop}" if crop else "for your field"

    # =========================================================================
    # 1. HARDWARE & TELEMETRY ALERTS
    # =========================================================================
    if reading is None or not reading.is_online:
        alerts.append(
            FarmAlert(
                id="alert_sensor_offline",
                severity="CRITICAL",
                title="Sensor Probe Offline",
                message="Field sensor probe is disconnected or offline. Automated telemetry monitoring is suspended.",
                source="hardware",
                timestamp=getattr(reading, "last_updated", "") or now_str,
                is_active=True,
                recommended_action="Inspect field node power supply, probe cable contact, and solar battery connection.",
            )
        )
    else:
        raw_status = (getattr(reading, "raw_status", "ok") or "ok").strip().lower()
        if raw_status in FAULT_STATUSES:
            alerts.append(
                FarmAlert(
                    id=f"alert_hardware_fault_{raw_status}",
                    severity="CRITICAL",
                    title="Hardware Diagnostic Fault",
                    message=f"Hardware reported explicit probe fault ({raw_status}). Telemetry may be unreliable.",
                    source="hardware",
                    timestamp=reading.last_updated or now_str,
                    is_active=True,
                    recommended_action="Clean probe pins and verify physical analog/digital electrical continuity.",
                )
            )
        elif raw_status in ("stale_or_offline", "no_signal"):
            alerts.append(
                FarmAlert(
                    id="alert_stale_telemetry",
                    severity="ALERT",
                    title="Telemetry Signal Stale",
                    message="Field transmission delayed. Telemetry has not refreshed within normal expected window.",
                    source="hardware",
                    timestamp=reading.last_updated or now_str,
                    is_active=True,
                    recommended_action="Verify Wi-Fi/mesh signal strength and antenna line-of-sight.",
                )
            )

        # Battery warning
        batt = getattr(reading, "battery_voltage", None)
        if batt is not None and batt < 3.4:
            alerts.append(
                FarmAlert(
                    id="alert_battery_low",
                    severity="WARNING",
                    title="Sensor Node Battery Low",
                    message=f"ESP32 node battery voltage has dropped to {batt:.2f}V (threshold 3.40V).",
                    source="hardware",
                    timestamp=reading.last_updated or now_str,
                    is_active=True,
                    recommended_action="Ensure solar charging panel is clean and oriented toward direct sunlight.",
                )
            )

    # =========================================================================
    # 2. SOIL MOISTURE & IRRIGATION ALERTS (Only if telemetry is reliable)
    # =========================================================================
    if reading and reading.is_online and getattr(reading, "raw_status", "ok") not in FAULT_STATUSES:
        sm = reading.soil_moisture
        if sm < 30.0:
            # Check if weather suggests holding off due to rain
            rain_prob = getattr(weather, "precipitation_probability", 0) if weather else 0
            if rain_prob >= 60:
                alerts.append(
                    FarmAlert(
                        id="alert_irrigation_hold_rain",
                        severity="WARNING",
                        title="Hold Irrigation — Rain Imminent",
                        message=f"Soil moisture is low ({sm:.0f}%), but rain probability is {rain_prob}%. Natural precipitation will recharge root zone.",
                        source="irrigation",
                        timestamp=now_str,
                        is_active=True,
                        recommended_action="Delay scheduled watering by 12 hours to avoid over-saturation and save water.",
                    )
                )
            else:
                alerts.append(
                    FarmAlert(
                        id="alert_soil_moisture_deficit",
                        severity="ALERT",
                        title="Soil Moisture Deficit",
                        message=f"Soil moisture is at {sm:.0f}%, which is below the 30% healthy threshold {crop_name}.",
                        source="irrigation",
                        timestamp=now_str,
                        is_active=True,
                        recommended_action="Irrigate the crop according to your irrigation schedule to prevent plant moisture stress.",
                    )
                )
        elif sm > 70.0:
            alerts.append(
                FarmAlert(
                    id="alert_soil_waterlogging",
                    severity="WARNING",
                    title="Excessive Soil Moisture",
                    message=f"Soil moisture is elevated at {sm:.0f}%, which may impede root-zone aeration if sustained.",
                    source="irrigation",
                    timestamp=now_str,
                    is_active=True,
                    recommended_action="Cease all watering and inspect drainage furrows to ensure excess water drains freely.",
                )
            )

        # Thermal stress
        if reading.temperature > 35.0:
            alerts.append(
                FarmAlert(
                    id="alert_heat_stress",
                    severity="WARNING",
                    title="Elevated Canopy Temperature",
                    message=f"Field temperature has reached {reading.temperature:.0f}°C, increasing transpiration demand {crop_name}.",
                    source="sensor",
                    timestamp=now_str,
                    is_active=True,
                    recommended_action="Apply water during cool early morning or late evening hours to minimize evaporation loss.",
                )
            )

    # =========================================================================
    # 3. WEATHER & MICROCLIMATE ALERTS
    # =========================================================================
    if weather and getattr(weather, "is_available", True):
        wind_spd = getattr(weather, "wind_speed_kmh", 0.0)
        rain_prob = getattr(weather, "precipitation_probability", 0)
        rain_mm = getattr(weather, "precipitation_amount_mm", 0.0)

        if wind_spd > 20.0:
            alerts.append(
                FarmAlert(
                    id="alert_weather_high_wind",
                    severity="WARNING",
                    title="High Wind Speed Advisory",
                    message=f"Wind speeds are currently {wind_spd:.1f} km/h. Foliar spraying carries high drift risk.",
                    source="weather",
                    timestamp=now_str,
                    is_active=True,
                    recommended_action="Postpone foliar nutrient or bio-spray applications until winds subside below 15 km/h.",
                )
            )

        if rain_prob >= 75 and rain_mm >= 15.0:
            alerts.append(
                FarmAlert(
                    id="alert_weather_heavy_rain",
                    severity="ALERT",
                    title="Heavy Rainfall Warning",
                    message=f"Heavy rain forecasted ({rain_prob}% chance, ~{rain_mm:.1f} mm). Risk of surface ponding.",
                    source="weather",
                    timestamp=now_str,
                    is_active=True,
                    recommended_action="Clear bund outlets and field runoff ditches before precipitation begins.",
                )
            )

    # =========================================================================
    # 4. PLANT VISION SCREENING ADVISORIES
    # =========================================================================
    if vision_result and getattr(vision_result, "success", False):
        if not getattr(vision_result, "healthy", True):
            urgency = getattr(vision_result, "treatment_urgency", "moderate")
            v_sev = "ALERT" if urgency == "immediate" else "WARNING"
            alerts.append(
                FarmAlert(
                    id=f"alert_vision_{vision_result.disease_code.lower()}",
                    severity=v_sev,
                    title=f"Leaf Screening: {vision_result.diagnosis}",
                    message=f"Visual signs consistent with {vision_result.diagnosis} observed on foliage (~{vision_result.affected_foliage_ratio*100:.1f}% affected).",
                    source="vision",
                    timestamp=getattr(vision_result, "timestamp", "") or now_str,
                    is_active=True,
                    recommended_action=vision_result.recommended_action,
                )
            )
            # High humidity compound alert
            hum = getattr(reading, "humidity", 0.0) if reading else 0.0
            if hum > 75.0:
                alerts.append(
                    FarmAlert(
                        id="alert_compound_foliar_humidity",
                        severity="ALERT",
                        title="Canopy Humidity & Foliar Risk",
                        message=f"High relative humidity ({hum:.0f}%) combined with observed foliar lesions may promote symptom spread.",
                        source="farm_intelligence",
                        timestamp=now_str,
                        is_active=True,
                        recommended_action="Improve canopy aeration, avoid overhead sprinkler wetting, and monitor nearby rows.",
                    )
                )

    # If no alerts triggered, emit stable positive condition alert
    if not alerts:
        alerts.append(
            FarmAlert(
                id="alert_status_optimal",
                severity="GOOD",
                title="Stable Farm Conditions",
                message=f"Soil moisture, ambient temperature, and telemetry are within balanced agronomic limits {crop_name}.",
                source="farm_intelligence",
                timestamp=now_str,
                is_active=True,
                recommended_action="Maintain routine crop observation and scheduled monitoring.",
            )
        )

    # Deterministic sort: Severity descending, then source
    alerts.sort(key=lambda a: a.severity_weight, reverse=True)
    return alerts
