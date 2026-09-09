"""Tests for ai_service, irrigation_service, and sensor_service telemetry."""

import unittest
from services.ai_service import get_ai_response
from services.irrigation_service import IrrigationStatus, get_irrigation_status
from services.sensor_service import SensorReading, get_current_sensor_data
from services.sensor_simulator import CONDITION_DRY, CONDITION_OFFLINE, CONDITION_NORMAL


class TestSensorService(unittest.TestCase):
    def test_sensor_reading_backward_compatibility(self):
        # 3 positional arguments continue to work identically
        reading = SensorReading(35.5, 24.0, 60.0)
        self.assertEqual(reading.soil_moisture, 35.5)
        self.assertEqual(reading.temperature, 24.0)
        self.assertEqual(reading.humidity, 60.0)
        self.assertTrue(reading.is_online)
        self.assertEqual(reading.source, "simulation")

    def test_get_current_sensor_data_default(self):
        reading = get_current_sensor_data()
        self.assertIsInstance(reading, SensorReading)
        self.assertTrue(reading.is_online)
        self.assertTrue(reading.soil_moisture > 0)

    def test_get_current_sensor_data_dry_and_offline(self):
        dry = get_current_sensor_data(condition=CONDITION_DRY)
        self.assertTrue(dry.soil_moisture < 30.0)

        offline = get_current_sensor_data(condition=CONDITION_OFFLINE)
        self.assertFalse(offline.is_online)
        self.assertEqual(offline.soil_moisture, 0.0)

    def test_get_current_sensor_data_hardware_mode(self):
        from services.hardware_client import HardwareClient
        from services.telemetry_store import GLOBAL_TELEMETRY_STORE

        GLOBAL_TELEMETRY_STORE.clear()
        # Empty hardware store -> offline reading
        off_reading = get_current_sensor_data(mode="hardware")
        self.assertFalse(off_reading.is_online)
        self.assertEqual(off_reading.source, "hardware")
        self.assertEqual(off_reading.soil_moisture, 0.0)

        # Ingest mock hardware packet
        HardwareClient.ingest({
            "device_id": "esp32-node-99",
            "soil_moisture": 48.5,
            "temperature": 27.5,
            "humidity": 65.0,
            "battery_voltage": 4.15,
            "wifi_rssi": -60,
        })
        hw_reading = get_current_sensor_data(mode="hardware")
        self.assertTrue(hw_reading.is_online)
        self.assertEqual(hw_reading.source, "hardware")
        self.assertEqual(hw_reading.device_id, "esp32-node-99")
        self.assertEqual(hw_reading.soil_moisture, 48.5)
        self.assertEqual(hw_reading.battery_voltage, 4.15)
        self.assertEqual(hw_reading.wifi_rssi, -60)
        GLOBAL_TELEMETRY_STORE.clear()

    def test_sensor_reading_hardware_fields(self):
        reading = SensorReading(
            soil_moisture=40.0,
            temperature=25.0,
            humidity=55.0,
            is_online=True,
            device_id="esp32-01",
            battery_voltage=3.85,
            wifi_rssi=-70,
            sensor_timestamp="2026-09-09T16:00:00Z",
            raw_status="ok",
        )
        self.assertEqual(reading.device_id, "esp32-01")
        self.assertEqual(reading.battery_voltage, 3.85)
        self.assertEqual(reading.wifi_rssi, -70)
        self.assertEqual(reading.sensor_timestamp, "2026-09-09T16:00:00Z")
        self.assertEqual(reading.raw_status, "ok")


class TestIrrigationService(unittest.TestCase):
    def test_thresholds_without_context(self):
        # Low moisture (< 30) -> water needed (alert)
        res_low = get_irrigation_status(25.0)
        self.assertTrue(res_low.needs_water)
        self.assertEqual(res_low.status_type, "alert")
        self.assertEqual(res_low.label, "Water Needed")

        # Healthy moisture (30 to 60) -> not required (good)
        res_ok = get_irrigation_status(45.0)
        self.assertFalse(res_ok.needs_water)
        self.assertEqual(res_ok.status_type, "good")
        self.assertEqual(res_ok.label, "Not Required")

        # Wet moisture (> 60) -> not required (warning)
        res_wet = get_irrigation_status(75.0)
        self.assertFalse(res_wet.needs_water)
        self.assertEqual(res_wet.status_type, "warning")
        self.assertEqual(res_wet.label, "Not Required")

    def test_irrigation_with_crop_context(self):
        ctx = {"crop": "Tomato"}
        res = get_irrigation_status(20.0, farm_context=ctx)
        self.assertTrue(res.needs_water)
        self.assertIn("Tomato", res.detail)

    def test_irrigation_with_offline_sensor(self):
        res_offline = get_irrigation_status(0.0, is_online=False)
        self.assertFalse(res_offline.needs_water)
        self.assertEqual(res_offline.label, "Sensor Offline")
        self.assertEqual(res_offline.status_type, "warning")
        self.assertIn("unavailable", res_offline.detail)

    def test_irrigation_with_probe_disconnected(self):
        # Disconnected probe reading 0.0 with raw_status="probe_disconnected"
        # Must NEVER trigger irrigation
        res_fault = get_irrigation_status(0.0, is_online=False, raw_status="probe_disconnected")
        self.assertFalse(res_fault.needs_water)
        self.assertEqual(res_fault.label, "Sensor Offline")
        self.assertIn("disconnected", res_fault.detail.lower())

        # Even if is_online was erroneously set to True, raw_status must override
        res_override = get_irrigation_status(0.0, is_online=True, raw_status="probe_disconnected")
        self.assertFalse(res_override.needs_water)
        self.assertEqual(res_override.label, "Sensor Offline")


class TestAiService(unittest.TestCase):
    def test_ai_response_without_context(self):
        # General response without context
        reply = get_ai_response("When should I water?")
        self.assertIn("30%", reply)
        self.assertIn("Irrigation card", reply)

        hello_reply = get_ai_response("Hello")
        self.assertIn("Hello", hello_reply)

    def test_ai_response_with_farm_context(self):
        ctx = {
            "crop": "Tomato",
            "growth_stage": "Flowering",
            "soil_type": "Loamy Soil",
            "irrigation_method": "Drip Irrigation",
            "farmer_name": "Ramesh",
        }

        # Water query should reference Tomato, Flowering, Loamy Soil
        water_reply = get_ai_response("Do I need to water my plants?", context=ctx)
        self.assertIn("Tomato", water_reply)
        self.assertIn("Flowering", water_reply)
        self.assertIn("Loamy Soil", water_reply)

        # Soil query should reference crop and soil
        soil_reply = get_ai_response("How is my soil?", context=ctx)
        self.assertIn("Tomato", soil_reply)
        self.assertIn("Loamy Soil", soil_reply)

        # Greeting should acknowledge farmer and crop
        greeting = get_ai_response("Hello", context=ctx)
        self.assertIn("Ramesh", greeting)
        self.assertIn("Tomato", greeting)

        # Summary inquiry
        summary = get_ai_response("What are my farm details?", context=ctx)
        self.assertIn("Tomato", summary)
        self.assertIn("Flowering", summary)

    def test_ai_response_with_live_telemetry(self):
        # Dry condition -> quotes 22% and recommends irrigation
        ctx_dry = {
            "crop": "Tomato",
            "soil_moisture": 22.0,
            "temperature": 32.0,
            "humidity": 40.0,
            "sensor_online": True,
        }
        water_reply = get_ai_response("Should I water my crop today?", context=ctx_dry)
        self.assertIn("22%", water_reply)
        self.assertIn("Irrigation is recommended", water_reply)

        # Temperature query -> quotes 32°C
        temp_reply = get_ai_response("What is the temperature on my farm?", context=ctx_dry)
        self.assertIn("32°C", temp_reply)

        # Sensor status query
        status_reply = get_ai_response("Is my sensor working?", context=ctx_dry)
        self.assertIn("online", status_reply)

    def test_ai_response_with_offline_sensor(self):
        ctx_offline = {
            "crop": "Tomato",
            "soil_moisture": 0.0,
            "sensor_online": False,
        }
        # Water query when sensor is offline -> warns offline and advises manual inspection
        water_reply = get_ai_response("Should I water my crop?", context=ctx_offline)
        self.assertIn("offline", water_reply)
        self.assertIn("manually", water_reply)

        # Sensor status query
        status_reply = get_ai_response("Is my sensor working?", context=ctx_offline)
        self.assertIn("offline", status_reply)

    def test_ai_response_does_not_fabricate_missing_fields(self):
        # Only crop is given, no variety, no soil, no stage
        ctx = {"crop": "Wheat"}
        reply = get_ai_response("What crop am I growing?", context=ctx)
        self.assertIn("Wheat", reply)
        # Should not fabricate variety or stage
        self.assertNotIn("Flowering", reply)
        self.assertNotIn("Loamy", reply)


if __name__ == "__main__":
    unittest.main()
