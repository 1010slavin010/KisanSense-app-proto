"""Lightweight HTTP telemetry ingestion server for KisanSense.

Provides a dedicated REST endpoint for ESP32 field microcontrollers
running over local Wi-Fi or LAN. Accepts incoming JSON payloads,
enforces X-Sensor-Key authentication, validates telemetry, and
persists readings to the shared TelemetryStore without blocking Streamlit.
"""

from __future__ import annotations

from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import logging
import os
import socketserver
import threading
from typing import Any

from services.hardware_client import HardwareClient, get_configured_sensor_key

logger = logging.getLogger("kisansense.telemetry_server")

# Default HTTP Ingestion Port
DEFAULT_HTTP_PORT = 8502
TELEMETRY_ENDPOINT = "/api/v1/telemetry"
HEALTH_ENDPOINT = "/api/v1/health"


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    """Multi-threaded HTTP server allowing non-blocking ingestion."""
    daemon_threads = True
    allow_reuse_address = True


class TelemetryRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for ESP32 telemetry ingestion."""

    def _send_json_response(self, status_code: int, payload: dict[str, Any]) -> None:
        response_data = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response_data)))
        self.end_headers()
        self.wfile.write(response_data)

    def do_GET(self) -> None:  # noqa: N802
        if self.path in (HEALTH_ENDPOINT, "/health"):
            self._send_json_response(200, {
                "status": "healthy",
                "service": "kisansense-telemetry-server",
                "endpoint": TELEMETRY_ENDPOINT,
            })
        else:
            self._send_json_response(404, {
                "error": "Not Found",
                "detail": f"Path '{self.path}' not recognized. Use {TELEMETRY_ENDPOINT}.",
            })

    def do_POST(self) -> None:  # noqa: N802
        if self.path != TELEMETRY_ENDPOINT:
            self._send_json_response(404, {
                "error": "Not Found",
                "detail": f"Unknown endpoint '{self.path}'. Use POST {TELEMETRY_ENDPOINT}.",
            })
            return

        # 1. Enforce Authentication Header
        configured_key = get_configured_sensor_key()
        provided_key = (
            self.headers.get("X-Sensor-Key")
            or self.headers.get("x-sensor-key")
        )

        # Fallback: check Authorization: Bearer <token>
        auth_header = self.headers.get("Authorization", "")
        if not provided_key and auth_header.startswith("Bearer "):
            provided_key = auth_header.split(" ", 1)[1].strip()

        # If a sensor key is configured, strictly enforce match
        if configured_key:
            if not provided_key or provided_key != configured_key:
                self._send_json_response(401, {
                    "error": "Unauthorized",
                    "detail": "Missing or invalid X-Sensor-Key authentication header.",
                })
                return

        # 2. Read and Parse Body
        content_length_header = self.headers.get("Content-Length")
        if not content_length_header:
            self._send_json_response(411, {
                "error": "Length Required",
                "detail": "Missing Content-Length header.",
            })
            return

        try:
            content_length = int(content_length_header)
            raw_body = self.rfile.read(content_length).decode("utf-8")
        except Exception as exc:
            self._send_json_response(400, {
                "error": "Bad Request",
                "detail": f"Failed to read HTTP body: {exc}",
            })
            return

        # 3. Validate and Ingest via HardwareClient
        success, msg, cleaned = HardwareClient.ingest_with_result(
            raw_body, expected_api_key=configured_key, provided_api_key=provided_key
        )

        if not success:
            status_code = 401 if "Unauthorized" in msg else 422
            self._send_json_response(status_code, {
                "error": "Unprocessable Entity" if status_code == 422 else "Unauthorized",
                "detail": msg,
            })
            return

        self._send_json_response(200, {
            "status": "ok",
            "message": "Telemetry accepted and stored",
            "device_id": cleaned.get("device_id", ""),
            "soil_moisture": cleaned.get("soil_moisture"),
            "temperature": cleaned.get("temperature"),
            "humidity": cleaned.get("humidity"),
        })

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        # Suppress noisy standard HTTP access logging during tests
        if os.environ.get("KISANSENSE_DEBUG_HTTP") == "1":
            logger.info("%s - - [%s] %s\n", self.address_string(), self.log_date_time_string(), format % args)


# Global Server State
_SERVER_LOCK = threading.Lock()
_ACTIVE_SERVER: HTTPServer | None = None
_ACTIVE_THREAD: threading.Thread | None = None


def start_telemetry_server(
    host: str = "0.0.0.0", port: int | None = None
) -> tuple[HTTPServer, int]:
    """Start the background HTTP telemetry server.

    Returns:
        (server_instance, bound_port)
    """
    global _ACTIVE_SERVER, _ACTIVE_THREAD

    with _SERVER_LOCK:
        if _ACTIVE_SERVER is not None:
            bound_port = _ACTIVE_SERVER.server_port
            return _ACTIVE_SERVER, bound_port

        effective_port = port or int(os.environ.get("KISANSENSE_HTTP_PORT", DEFAULT_HTTP_PORT))
        server = ThreadedHTTPServer((host, effective_port), TelemetryRequestHandler)
        actual_port = server.server_port

        thread = threading.Thread(
            target=server.serve_forever,
            name="KisanSenseTelemetryServerThread",
            daemon=True,
        )
        thread.start()

        _ACTIVE_SERVER = server
        _ACTIVE_THREAD = thread
        logger.info("Telemetry server listening on http://%s:%d%s", host, actual_port, TELEMETRY_ENDPOINT)
        return server, actual_port


def stop_telemetry_server() -> None:
    """Stop the background HTTP telemetry server cleanly."""
    global _ACTIVE_SERVER, _ACTIVE_THREAD

    with _SERVER_LOCK:
        if _ACTIVE_SERVER is not None:
            _ACTIVE_SERVER.shutdown()
            _ACTIVE_SERVER.server_close()
            _ACTIVE_SERVER = None
            _ACTIVE_THREAD = None
            logger.info("Telemetry server stopped.")


def is_telemetry_server_running() -> bool:
    """Return True if the background HTTP server is currently active."""
    with _SERVER_LOCK:
        return _ACTIVE_SERVER is not None
