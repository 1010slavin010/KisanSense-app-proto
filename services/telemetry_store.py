"""Thread-safe in-memory store for incoming ESP32 telemetry.

Acts as the temporary buffer between the ingestion layer (REST webhook / API)
and the sensor service. Supports multi-device tracking, staleness expiration,
and thread-safe reads/writes.
"""

from __future__ import annotations

from datetime import datetime, timezone
import threading
from typing import Any

# Default staleness threshold in seconds (5 minutes)
DEFAULT_STALENESS_SECONDS = 300


class TelemetryStore:
    """Thread-safe telemetry cache."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._store: dict[str, dict[str, Any]] = {}
        self._latest_device_id: str | None = None

    def save_telemetry(self, payload: dict[str, Any]) -> None:
        """Store a validated telemetry payload."""
        device_id = payload.get("device_id", "default_device")
        now = datetime.now(timezone.utc)
        record = {
            "payload": dict(payload),
            "received_at": now,
        }
        with self._lock:
            self._store[device_id] = record
            self._latest_device_id = device_id

    def get_latest_telemetry(
        self, device_id: str | None = None, max_age_seconds: int = DEFAULT_STALENESS_SECONDS
    ) -> dict[str, Any] | None:
        """Retrieve the most recent telemetry record.

        Args:
            device_id: Target device identifier. If None, uses the last active device.
            max_age_seconds: Maximum age before telemetry is flagged as stale.

        Returns:
            The payload dictionary if available and within max_age_seconds,
            or None if no record exists or data is older than max_age_seconds.
        """
        with self._lock:
            target_id = device_id or self._latest_device_id
            if not target_id or target_id not in self._store:
                return None

            record = self._store[target_id]

        now = datetime.now(timezone.utc)
        age = (now - record["received_at"]).total_seconds()

        result = dict(record["payload"])
        result["age_seconds"] = round(age, 1)
        result["is_stale"] = age > max_age_seconds
        result["received_at_iso"] = record["received_at"].isoformat()
        return result

    def get_all_devices(self) -> list[str]:
        """Return list of known device IDs."""
        with self._lock:
            return list(self._store.keys())

    def clear(self) -> None:
        """Clear all stored telemetry."""
        with self._lock:
            self._store.clear()
            self._latest_device_id = None


# Singleton instance for process-wide access
GLOBAL_TELEMETRY_STORE = TelemetryStore()
