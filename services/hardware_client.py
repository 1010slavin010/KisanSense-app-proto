"""ESP32 hardware client and telemetry ingestion for KisanSense.

Validates incoming hardware payloads, enforces physical sanity bounds,
handles token authentication, performs sensor clock-skew verification,
handles explicit probe disconnect and sensor fault states, and translates
validated telemetry into the application's standard SensorReading contract.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from typing import Any

from services.telemetry_store import GLOBAL_TELEMETRY_STORE

# Physical bounds for validation
MOISTURE_MIN = 0.0
MOISTURE_MAX = 100.0
TEMP_MIN = -10.0
TEMP_MAX = 65.0
HUMIDITY_MIN = 0.0
HUMIDITY_MAX = 100.0
BATTERY_MIN = 2.0
BATTERY_MAX = 5.5
RSSI_MIN = -120
RSSI_MAX = 0

# Maximum allowed sensor timestamp clock-skew relative to server UTC (15 minutes)
MAX_TIMESTAMP_SKEW_SECONDS = 900

# Explicit hardware fault status identifiers
FAULT_STATUSES = {
    "probe_disconnected",
    "sensor_fault",
    "hardware_fault",
    "wire_fault",
    "adc_error",
    "fault",
}


def get_configured_sensor_key() -> str | None:
    """Retrieve the configured secret API key for ESP32 authentication.

    Checks:
    1. Streamlit secrets (st.secrets["telemetry"]["sensor_api_key"] or st.secrets["KISANSENSE_SENSOR_KEY"])
    2. Environment variable KISANSENSE_SENSOR_KEY
    """
    try:
        import streamlit as st

        if hasattr(st, "secrets") and "telemetry" in st.secrets:
            key = st.secrets["telemetry"].get("sensor_api_key")
            if key:
                return str(key).strip()
        if hasattr(st, "secrets") and "KISANSENSE_SENSOR_KEY" in st.secrets:
            return str(st.secrets["KISANSENSE_SENSOR_KEY"]).strip()
    except Exception:
        pass

    env_key = os.environ.get("KISANSENSE_SENSOR_KEY")
    return env_key.strip() if env_key else None


def validate_telemetry_payload(
    raw_data: Any,
    expected_api_key: str | None = None,
    provided_api_key: str | None = None,
    check_timestamp_skew: bool = True,
) -> tuple[bool, str, dict[str, Any]]:
    """Validate incoming ESP32 telemetry.

    Returns:
        (is_valid, error_message, cleaned_payload)
    """
    if isinstance(raw_data, str):
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError as exc:
            return False, f"Malformed JSON: {exc}", {}
    elif isinstance(raw_data, dict):
        data = dict(raw_data)
    else:
        return False, "Payload must be a JSON string or dict", {}

    # 1. API key authentication enforcement
    if expected_api_key:
        api_key = provided_api_key or data.get("api_key") or data.get("token")
        if not api_key or api_key != expected_api_key:
            return False, "Unauthorized: Invalid or missing sensor key", {}

    # 2. Device ID
    device_id = data.get("device_id")
    if not device_id or not str(device_id).strip():
        return False, "Missing or empty required field: device_id", {}
    device_id = str(device_id).strip()

    # 3. Soil Moisture
    if "soil_moisture" not in data:
        return False, "Missing required field: soil_moisture", {}
    try:
        soil_moisture = float(data["soil_moisture"])
        if not (MOISTURE_MIN <= soil_moisture <= MOISTURE_MAX):
            return False, f"soil_moisture {soil_moisture}% out of physical bounds [{MOISTURE_MIN}, {MOISTURE_MAX}]", {}
    except (ValueError, TypeError):
        return False, "soil_moisture must be a valid number", {}

    # 4. Temperature
    if "temperature" not in data:
        return False, "Missing required field: temperature", {}
    try:
        temperature = float(data["temperature"])
        if not (TEMP_MIN <= temperature <= TEMP_MAX):
            return False, f"temperature {temperature}°C out of physical bounds [{TEMP_MIN}, {TEMP_MAX}]", {}
    except (ValueError, TypeError):
        return False, "temperature must be a valid number", {}

    # 5. Humidity
    if "humidity" not in data:
        return False, "Missing required field: humidity", {}
    try:
        humidity = float(data["humidity"])
        if not (HUMIDITY_MIN <= humidity <= HUMIDITY_MAX):
            return False, f"humidity {humidity}% out of physical bounds [{HUMIDITY_MIN}, {HUMIDITY_MAX}]", {}
    except (ValueError, TypeError):
        return False, "humidity must be a valid number", {}

    # 6. Optional Battery Voltage
    battery_voltage: float | None = None
    if "battery_voltage" in data and data["battery_voltage"] is not None:
        try:
            b_val = float(data["battery_voltage"])
            if BATTERY_MIN <= b_val <= BATTERY_MAX:
                battery_voltage = round(b_val, 2)
        except (ValueError, TypeError):
            pass

    # 7. Optional WiFi RSSI
    wifi_rssi: int | None = None
    if "wifi_rssi" in data and data["wifi_rssi"] is not None:
        try:
            r_val = int(data["wifi_rssi"])
            if RSSI_MIN <= r_val <= RSSI_MAX:
                wifi_rssi = r_val
        except (ValueError, TypeError):
            pass

    # 8. Raw Status / Explicit Fault Flag
    raw_status = str(data.get("raw_status", "ok")).strip().lower()
    if not raw_status:
        raw_status = "ok"

    # 9. Timestamp & Clock-Skew Validation
    timestamp_str = str(data.get("timestamp", "")).strip()
    if timestamp_str and check_timestamp_skew:
        try:
            # Normalize ISO string with Z to +00:00 for datetime parsing
            parsed_ts = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            if parsed_ts.tzinfo is None:
                parsed_ts = parsed_ts.replace(tzinfo=timezone.utc)
            now_utc = datetime.now(timezone.utc)
            skew_seconds = abs((now_utc - parsed_ts).total_seconds())
            if skew_seconds > MAX_TIMESTAMP_SKEW_SECONDS:
                return (
                    False,
                    f"Sensor timestamp '{timestamp_str}' exceeds maximum allowed clock skew "
                    f"({MAX_TIMESTAMP_SKEW_SECONDS} seconds from server UTC)",
                    {},
                )
        except Exception:
            return False, f"Malformed ISO 8601 sensor timestamp: '{timestamp_str}'", {}

    cleaned: dict[str, Any] = {
        "device_id": device_id,
        "soil_moisture": round(soil_moisture, 1),
        "temperature": round(temperature, 1),
        "humidity": round(humidity, 1),
        "battery_voltage": battery_voltage,
        "wifi_rssi": wifi_rssi,
        "timestamp": timestamp_str,
        "raw_status": raw_status,
    }
    return True, "Valid", cleaned


class HardwareClient:
    """Interface for processing and retrieving hardware telemetry."""

    @staticmethod
    def ingest(
        raw_data: Any,
        expected_api_key: str | None = None,
        provided_api_key: str | None = None,
        check_timestamp_skew: bool = True,
    ) -> tuple[bool, str]:
        """Validate and buffer incoming telemetry from ESP32."""
        success, msg, _ = HardwareClient.ingest_with_result(
            raw_data=raw_data,
            expected_api_key=expected_api_key,
            provided_api_key=provided_api_key,
            check_timestamp_skew=check_timestamp_skew,
        )
        return success, msg

    @staticmethod
    def ingest_with_result(
        raw_data: Any,
        expected_api_key: str | None = None,
        provided_api_key: str | None = None,
        check_timestamp_skew: bool = True,
    ) -> tuple[bool, str, dict[str, Any]]:
        """Validate, persist, and return the cleaned telemetry dictionary."""
        effective_key = expected_api_key if expected_api_key is not None else get_configured_sensor_key()

        is_valid, msg, cleaned = validate_telemetry_payload(
            raw_data=raw_data,
            expected_api_key=effective_key,
            provided_api_key=provided_api_key,
            check_timestamp_skew=check_timestamp_skew,
        )
        if not is_valid:
            return False, msg, {}

        GLOBAL_TELEMETRY_STORE.save_telemetry(cleaned)
        return True, "Telemetry ingested successfully", cleaned

    @staticmethod
    def get_reading(device_id: str | None = None) -> dict[str, Any]:
        """Fetch the latest hardware telemetry converted for SensorReading.

        Returns a dictionary suitable for instantiating SensorReading.
        """
        record = GLOBAL_TELEMETRY_STORE.get_latest_telemetry(device_id=device_id)

        # 1. No record or Stale timeout (> 300 seconds without packet)
        if not record or record.get("is_stale", True):
            target_id = device_id or (record.get("device_id") if record else "")
            return {
                "soil_moisture": 0.0,
                "temperature": 0.0,
                "humidity": 0.0,
                "is_online": False,
                "last_updated": record.get("received_at_iso", "") if record else "",
                "source": "hardware",
                "condition": "SENSOR_OFFLINE",
                "device_id": target_id,
                "battery_voltage": record.get("battery_voltage") if record else None,
                "wifi_rssi": record.get("wifi_rssi") if record else None,
                "sensor_timestamp": record.get("timestamp", "") if record else "",
                "raw_status": "stale_or_offline" if record else "no_signal",
            }

        # 2. Explicit Hardware Sensor Fault (e.g. Probe Disconnect)
        raw_status = record.get("raw_status", "ok")
        if raw_status in FAULT_STATUSES:
            return {
                "soil_moisture": 0.0,
                "temperature": 0.0,
                "humidity": 0.0,
                "is_online": False,
                "last_updated": record.get("received_at_iso", ""),
                "source": "hardware",
                "condition": "SENSOR_OFFLINE",
                "device_id": record.get("device_id", ""),
                "battery_voltage": record.get("battery_voltage"),
                "wifi_rssi": record.get("wifi_rssi"),
                "sensor_timestamp": record.get("timestamp", ""),
                "raw_status": raw_status,
            }

        # 3. Healthy Active Telemetry
        return {
            "soil_moisture": record["soil_moisture"],
            "temperature": record["temperature"],
            "humidity": record["humidity"],
            "is_online": True,
            "last_updated": record.get("received_at_iso", ""),
            "source": "hardware",
            "condition": "NORMAL",
            "device_id": record["device_id"],
            "battery_voltage": record.get("battery_voltage"),
            "wifi_rssi": record.get("wifi_rssi"),
            "sensor_timestamp": record.get("timestamp", ""),
            "raw_status": "ok",
        }
