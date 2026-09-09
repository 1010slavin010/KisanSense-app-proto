"""Unit and HTTP integration tests for ESP32 HardwareClient and TelemetryServer.

Validates payload schema rules, clock-skew checks, probe-disconnect fault handling,
token authentication, and live HTTP POST telemetry ingestion over loopback sockets.
"""

from datetime import datetime, timedelta, timezone
import json
import os
import unittest
import urllib.error
import urllib.request

from services.hardware_client import (
    FAULT_STATUSES,
    HardwareClient,
    get_configured_sensor_key,
    validate_telemetry_payload,
)
from services.sensor_service import get_current_sensor_data
from services.telemetry_server import (
    start_telemetry_server,
    stop_telemetry_server,
)
from services.telemetry_store import GLOBAL_TELEMETRY_STORE, TelemetryStore


class TestHardwareClient(unittest.TestCase):
    def setUp(self):
        GLOBAL_TELEMETRY_STORE.clear()

    def tearDown(self):
        GLOBAL_TELEMETRY_STORE.clear()

    def test_validate_valid_payload(self):
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        payload = {
            "device_id": "esp32-zone-1",
            "soil_moisture": 36.5,
            "temperature": 28.0,
            "humidity": 62.0,
            "battery_voltage": 3.95,
            "wifi_rssi": -65,
            "timestamp": now_iso,
        }
        valid, msg, cleaned = validate_telemetry_payload(payload)
        self.assertTrue(valid, msg)
        self.assertEqual(cleaned["device_id"], "esp32-zone-1")
        self.assertEqual(cleaned["soil_moisture"], 36.5)
        self.assertEqual(cleaned["battery_voltage"], 3.95)
        self.assertEqual(cleaned["raw_status"], "ok")

    def test_validate_missing_fields(self):
        # Missing device_id
        valid, msg, _ = validate_telemetry_payload({"soil_moisture": 30, "temperature": 25, "humidity": 60})
        self.assertFalse(valid)
        self.assertIn("device_id", msg)

        # Missing soil_moisture
        valid, msg, _ = validate_telemetry_payload({"device_id": "d1", "temperature": 25, "humidity": 60})
        self.assertFalse(valid)
        self.assertIn("soil_moisture", msg)

        # Missing temperature
        valid, msg, _ = validate_telemetry_payload({"device_id": "d1", "soil_moisture": 40, "humidity": 60})
        self.assertFalse(valid)
        self.assertIn("temperature", msg)

        # Missing humidity
        valid, msg, _ = validate_telemetry_payload({"device_id": "d1", "soil_moisture": 40, "temperature": 25})
        self.assertFalse(valid)
        self.assertIn("humidity", msg)

    def test_validate_out_of_bounds(self):
        # Moisture > 100%
        valid, msg, _ = validate_telemetry_payload({
            "device_id": "d1", "soil_moisture": 110.0, "temperature": 25, "humidity": 60
        }, check_timestamp_skew=False)
        self.assertFalse(valid)
        self.assertIn("bounds", msg)

        # Moisture < 0%
        valid, msg, _ = validate_telemetry_payload({
            "device_id": "d1", "soil_moisture": -5.0, "temperature": 25, "humidity": 60
        }, check_timestamp_skew=False)
        self.assertFalse(valid)
        self.assertIn("bounds", msg)

        # Disconnected temperature probe (-127°C)
        valid, msg, _ = validate_telemetry_payload({
            "device_id": "d1", "soil_moisture": 30.0, "temperature": -127.0, "humidity": 60
        }, check_timestamp_skew=False)
        self.assertFalse(valid)
        self.assertIn("bounds", msg)

        # Temperature too high (> 65°C)
        valid, msg, _ = validate_telemetry_payload({
            "device_id": "d1", "soil_moisture": 30.0, "temperature": 75.0, "humidity": 60
        }, check_timestamp_skew=False)
        self.assertFalse(valid)
        self.assertIn("bounds", msg)

        # Humidity out of bounds
        valid, msg, _ = validate_telemetry_payload({
            "device_id": "d1", "soil_moisture": 30.0, "temperature": 25.0, "humidity": 120.0
        }, check_timestamp_skew=False)
        self.assertFalse(valid)
        self.assertIn("bounds", msg)

    def test_validate_malformed_json(self):
        valid, msg, _ = validate_telemetry_payload("not-valid-json-string{{{")
        self.assertFalse(valid)
        self.assertIn("Malformed JSON", msg)

        valid_list, msg_list, _ = validate_telemetry_payload([1, 2, 3])
        self.assertFalse(valid_list)
        self.assertIn("JSON string or dict", msg_list)

    def test_sensor_timestamp_validation(self):
        # 1. Valid recent timestamp (< 15 min old)
        recent_ts = (datetime.now(timezone.utc) - timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        valid, msg, _ = validate_telemetry_payload({
            "device_id": "d1", "soil_moisture": 40, "temperature": 25, "humidity": 55,
            "timestamp": recent_ts
        })
        self.assertTrue(valid, msg)

        # 2. Stale timestamp (> 15 minutes old: e.g. 2 hours old)
        stale_ts = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        valid_stale, msg_stale, _ = validate_telemetry_payload({
            "device_id": "d1", "soil_moisture": 40, "temperature": 25, "humidity": 55,
            "timestamp": stale_ts
        })
        self.assertFalse(valid_stale)
        self.assertIn("clock skew", msg_stale)

        # 3. Future timestamp (> 15 minutes ahead)
        future_ts = (datetime.now(timezone.utc) + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        valid_future, msg_future, _ = validate_telemetry_payload({
            "device_id": "d1", "soil_moisture": 40, "temperature": 25, "humidity": 55,
            "timestamp": future_ts
        })
        self.assertFalse(valid_future)
        self.assertIn("clock skew", msg_future)

        # 4. Malformed timestamp string
        valid_bad, msg_bad, _ = validate_telemetry_payload({
            "device_id": "d1", "soil_moisture": 40, "temperature": 25, "humidity": 55,
            "timestamp": "yesterday afternoon"
        })
        self.assertFalse(valid_bad)
        self.assertIn("Malformed ISO", msg_bad)

    def test_probe_disconnect_fault_handling(self):
        # Disconnected capacitive probe reports 0.0 with raw_status="probe_disconnected"
        payload = {
            "device_id": "esp32-node-fault",
            "soil_moisture": 0.0,
            "temperature": 25.0,
            "humidity": 55.0,
            "raw_status": "probe_disconnected",
        }
        success, msg = HardwareClient.ingest(payload, check_timestamp_skew=False)
        self.assertTrue(success, msg)

        reading = HardwareClient.get_reading(device_id="esp32-node-fault")
        # Must be flagged offline and fault state preserved
        self.assertFalse(reading["is_online"])
        self.assertEqual(reading["condition"], "SENSOR_OFFLINE")
        self.assertEqual(reading["raw_status"], "probe_disconnected")

    def test_api_key_authentication(self):
        payload = {
            "device_id": "d1", "soil_moisture": 40, "temperature": 25, "humidity": 50,
            "api_key": "secret_token_123"
        }
        # Correct key in payload
        valid, _, _ = validate_telemetry_payload(payload, expected_api_key="secret_token_123", check_timestamp_skew=False)
        self.assertTrue(valid)

        # Correct key in provided_api_key argument (e.g. from header)
        valid_hdr, _, _ = validate_telemetry_payload(
            {"device_id": "d1", "soil_moisture": 40, "temperature": 25, "humidity": 50},
            expected_api_key="secret_token_123",
            provided_api_key="secret_token_123",
            check_timestamp_skew=False,
        )
        self.assertTrue(valid_hdr)

        # Wrong key
        valid_wrong, msg_wrong, _ = validate_telemetry_payload(
            payload, expected_api_key="different_key", check_timestamp_skew=False
        )
        self.assertFalse(valid_wrong)
        self.assertIn("Unauthorized", msg_wrong)

        # Missing key when expected
        valid_missing, msg_missing, _ = validate_telemetry_payload(
            {"device_id": "d1", "soil_moisture": 40, "temperature": 25, "humidity": 50},
            expected_api_key="secret_token_123",
            check_timestamp_skew=False,
        )
        self.assertFalse(valid_missing)
        self.assertIn("Unauthorized", msg_missing)

    def test_telemetry_store_staleness(self):
        store = TelemetryStore()
        store.save_telemetry({"device_id": "node_a", "soil_moisture": 45.0})

        # Fresh query within 300s window
        record = store.get_latest_telemetry(max_age_seconds=60)
        self.assertIsNotNone(record)
        self.assertFalse(record["is_stale"])

        # Stale query (simulated timeout)
        record_stale = store.get_latest_telemetry(max_age_seconds=-1)
        self.assertTrue(record_stale["is_stale"])

    def test_hardware_client_ingest_and_get_reading(self):
        # Empty store -> offline
        reading_empty = HardwareClient.get_reading(device_id="esp32-field-01")
        self.assertFalse(reading_empty["is_online"])
        self.assertEqual(reading_empty["source"], "hardware")

        # Ingest payload
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        payload = {
            "device_id": "esp32-field-01",
            "soil_moisture": 44.2,
            "temperature": 26.5,
            "humidity": 65.0,
            "battery_voltage": 4.10,
            "wifi_rssi": -72,
            "timestamp": now_iso,
        }
        success, msg = HardwareClient.ingest(payload)
        self.assertTrue(success, msg)

        # Retrieve reading
        reading = HardwareClient.get_reading(device_id="esp32-field-01")
        self.assertTrue(reading["is_online"])
        self.assertEqual(reading["soil_moisture"], 44.2)
        self.assertEqual(reading["battery_voltage"], 4.10)
        self.assertEqual(reading["source"], "hardware")
        self.assertEqual(reading["raw_status"], "ok")


class TestTelemetryServerHTTPIntegration(unittest.TestCase):
    """Real HTTP integration tests communicating with the TelemetryServer socket."""

    @classmethod
    def setUpClass(cls):
        # Use port 8585 for testing
        cls.test_port = 8585
        cls.server, cls.bound_port = start_telemetry_server(host="127.0.0.1", port=cls.test_port)
        cls.base_url = f"http://127.0.0.1:{cls.bound_port}"

    @classmethod
    def tearDownClass(cls):
        stop_telemetry_server()

    def setUp(self):
        GLOBAL_TELEMETRY_STORE.clear()
        # Set a test sensor secret key in environment
        os.environ["KISANSENSE_SENSOR_KEY"] = "test-esp32-secret-key-42"

    def tearDown(self):
        GLOBAL_TELEMETRY_STORE.clear()
        if "KISANSENSE_SENSOR_KEY" in os.environ:
            del os.environ["KISANSENSE_SENSOR_KEY"]

    def test_http_health_endpoint(self):
        health_url = f"{self.base_url}/api/v1/health"
        req = urllib.request.Request(health_url, method="GET")
        with urllib.request.urlopen(req, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "healthy")
            self.assertIn("endpoint", data)

    def test_http_post_telemetry_unauthorized_when_key_missing(self):
        telemetry_url = f"{self.base_url}/api/v1/telemetry"
        payload = {
            "device_id": "esp32-http-01",
            "soil_moisture": 45.0,
            "temperature": 27.0,
            "humidity": 60.0,
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            telemetry_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=3)
            self.fail("Expected HTTPError 401")
        except urllib.error.HTTPError as err:
            self.assertEqual(err.code, 401)
            err.close()

    def test_http_post_telemetry_unauthorized_when_key_invalid(self):
        telemetry_url = f"{self.base_url}/api/v1/telemetry"
        payload = {
            "device_id": "esp32-http-01",
            "soil_moisture": 45.0,
            "temperature": 27.0,
            "humidity": 60.0,
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            telemetry_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Sensor-Key": "wrong-secret-token",
            },
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=3)
            self.fail("Expected HTTPError 401")
        except urllib.error.HTTPError as err:
            self.assertEqual(err.code, 401)
            err.close()

    def test_http_post_telemetry_malformed_json(self):
        telemetry_url = f"{self.base_url}/api/v1/telemetry"
        body = b"NOT_VALID_JSON{{"
        req = urllib.request.Request(
            telemetry_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Sensor-Key": "test-esp32-secret-key-42",
            },
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=3)
            self.fail("Expected HTTPError 400 or 422")
        except urllib.error.HTTPError as err:
            self.assertIn(err.code, (400, 422))
            err.close()

    def test_http_post_telemetry_success_and_store_integration(self):
        telemetry_url = f"{self.base_url}/api/v1/telemetry"
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        payload = {
            "device_id": "esp32-http-node-verified",
            "soil_moisture": 41.8,
            "temperature": 26.3,
            "humidity": 63.5,
            "battery_voltage": 4.05,
            "wifi_rssi": -58,
            "timestamp": now_iso,
        }
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            telemetry_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Sensor-Key": "test-esp32-secret-key-42",
            },
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=3) as resp:
            self.assertEqual(resp.status, 200)
            res_data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(res_data["status"], "ok")
            self.assertEqual(res_data["device_id"], "esp32-http-node-verified")
            self.assertEqual(res_data["soil_moisture"], 41.8)

        # Verify reading reached TelemetryStore
        record = GLOBAL_TELEMETRY_STORE.get_latest_telemetry(device_id="esp32-http-node-verified")
        self.assertIsNotNone(record)
        self.assertEqual(record["soil_moisture"], 41.8)
        self.assertEqual(record["battery_voltage"], 4.05)

        # Verify reading reached sensor_service and SensorReading contract
        reading = get_current_sensor_data(device_id="esp32-http-node-verified", mode="hardware")
        self.assertTrue(reading.is_online)
        self.assertEqual(reading.source, "hardware")
        self.assertEqual(reading.soil_moisture, 41.8)
        self.assertEqual(reading.temperature, 26.3)
        self.assertEqual(reading.battery_voltage, 4.05)
        self.assertEqual(reading.wifi_rssi, -58)


if __name__ == "__main__":
    unittest.main()
