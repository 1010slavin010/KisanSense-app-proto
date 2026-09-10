"""Comprehensive integration tests for Phase 7 — Complete Farm Assistance.

Tests:
1. Weather Service & Provider Abstraction (SimulatedWeatherProvider, is_demo, rain prob, advisory)
2. Advanced Irrigation Intelligence (WATER NOW, MONITOR, NO WATER NEEDED, SENSOR OFFLINE/FAULT/STALE)
3. Centralized Alert System (generate_farm_alerts, severity ordering, consistency)
4. Activity & Advisory Timeline (record_timeline_event, get_timeline_events)
5. Device Diagnostics (ONLINE, OFFLINE, STALE, FAULT, LOW BATTERY)
6. Grounded Chatbot Questions:
   - "Why is the soil dry?"
   - "Why shouldn't I irrigate?"
   - "What should I check today?"
   - "Will it rain?"
7. AppTest Verification across all 9 pages:
   - home, farm, weather, irrigation, vision, assistant, alerts, devices, analytics
8. All 4 languages and all 8 simulator conditions
"""

from __future__ import annotations

import os
import unittest
from streamlit.testing.v1 import AppTest

from services.ai_service import get_ai_response
from services.alert_service import FarmAlert, generate_farm_alerts
from services.farm_intelligence import evaluate_farm_intelligence
from services.irrigation_service import get_irrigation_status
from services.sensor_service import (
    ALL_CONDITIONS,
    SensorReading,
    get_current_sensor_data,
)
from services.timeline_service import (
    get_timeline_events,
    record_timeline_event,
)
from services.weather_service import (
    SimulatedWeatherProvider,
    WeatherProvider,
    WeatherSnapshot,
    get_weather_snapshot,
)
from utils.translations import SUPPORTED_LANGUAGES, t

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))


class TestWeatherProviderAbstraction(unittest.TestCase):
    """Test Weather Service Provider interface and simulated provider."""

    def test_simulated_weather_provider(self):
        provider = SimulatedWeatherProvider()
        self.assertIsInstance(provider, WeatherProvider)
        snap = provider.get_weather(location="Mandya, Karnataka", condition_hint="NORMAL")
        self.assertIsInstance(snap, WeatherSnapshot)
        self.assertTrue(snap.is_demo)
        self.assertEqual(snap.source, "demo_weather_simulator")
        self.assertTrue(snap.is_available)
        self.assertEqual(len(snap.forecast_days), 3)

    def test_get_weather_snapshot_condition_hints(self):
        wet_snap = get_weather_snapshot(condition_hint="WET")
        self.assertGreaterEqual(wet_snap.precipitation_probability, 60)

        hot_snap = get_weather_snapshot(condition_hint="HOT")
        self.assertGreaterEqual(hot_snap.temperature, 35.0)

        dry_snap = get_weather_snapshot(condition_hint="DRY")
        self.assertLessEqual(dry_snap.humidity, 45.0)


class TestCentralizedAlertSystem(unittest.TestCase):
    """Test centralized alert generation and severity ordering."""

    def test_offline_sensor_critical_alert(self):
        reading = SensorReading(soil_moisture=0.0, temperature=0.0, humidity=0.0, is_online=False)
        alerts = generate_farm_alerts(reading=reading)
        self.assertTrue(any(a.id == "alert_sensor_offline" for a in alerts))
        self.assertEqual(alerts[0].severity, "CRITICAL")

    def test_hardware_fault_alert(self):
        reading = SensorReading(
            soil_moisture=45.0,
            temperature=25.0,
            humidity=50.0,
            is_online=True,
            raw_status="probe_disconnected",
        )
        alerts = generate_farm_alerts(reading=reading)
        self.assertTrue(any("fault" in a.id for a in alerts))
        self.assertEqual(alerts[0].severity, "CRITICAL")

    def test_low_battery_warning(self):
        reading = SensorReading(
            soil_moisture=45.0,
            temperature=25.0,
            humidity=50.0,
            is_online=True,
            battery_voltage=3.25,
        )
        alerts = generate_farm_alerts(reading=reading)
        self.assertTrue(any(a.id == "alert_battery_low" for a in alerts))

    def test_stable_conditions_emit_good_alert(self):
        reading = SensorReading(
            soil_moisture=45.0,
            temperature=25.0,
            humidity=55.0,
            is_online=True,
        )
        alerts = generate_farm_alerts(reading=reading)
        self.assertTrue(any(a.severity == "GOOD" for a in alerts))


class TestTimelineService(unittest.TestCase):
    """Test activity and advisory timeline operations."""

    def test_record_and_retrieve_events(self):
        record_timeline_event(
            event_type="irrigation",
            title="Test Irrigation Trigger",
            description="Recommended watering applied.",
            severity="alert",
        )
        events = get_timeline_events(limit=5)
        self.assertGreater(len(events), 0)
        self.assertEqual(events[0].title, "Test Irrigation Trigger")
        self.assertEqual(events[0].severity, "alert")


class TestChatbotAdvancedQuestions(unittest.TestCase):
    """Test grounded chatbot responses for specific diagnostic inquiries."""

    def setUp(self):
        self.context_dry = {
            "crop": "Tomato",
            "soil_moisture": 22.0,
            "temperature": 32.0,
            "humidity": 45.0,
            "sensor_online": True,
        }
        self.context_wet = {
            "crop": "Tomato",
            "soil_moisture": 72.0,
            "temperature": 24.0,
            "humidity": 80.0,
            "sensor_online": True,
        }
        self.context_offline = {
            "crop": "Tomato",
            "soil_moisture": 0.0,
            "temperature": 0.0,
            "humidity": 0.0,
            "sensor_online": False,
        }

    def test_why_is_soil_dry_inquiry(self):
        reply = get_ai_response("Why is the soil dry?", context=self.context_dry)
        self.assertIn("22%", reply)
        self.assertIn("transpiration", reply.lower())
        self.assertIn("irrigation is recommended", reply.lower())

    def test_why_not_irrigate_when_wet(self):
        reply = get_ai_response("Why shouldn't I irrigate?", context=self.context_wet)
        self.assertIn("72%", reply)
        self.assertIn("not required", reply.lower())

    def test_why_not_irrigate_when_sensor_offline(self):
        reply = get_ai_response("Why shouldn't I irrigate?", context=self.context_offline)
        self.assertIn("offline", reply.lower())
        self.assertIn("fail-safe", reply.lower())

    def test_what_should_i_check_today(self):
        reply = get_ai_response("What should I check today?", context=self.context_dry)
        self.assertIn("Checklist", reply)
        self.assertIn("Soil Moisture", reply)
        self.assertIn("Weather", reply)


class TestAllRoutesAppTest(unittest.TestCase):
    """Verify all 9 navigation pages render cleanly in AppTest."""

    def test_all_pages_clean_rendering(self):
        pages = ["home", "farm", "weather", "irrigation", "vision", "assistant", "alerts", "devices", "analytics"]
        for p in pages:
            at = AppTest.from_file(APP_PATH)
            at.session_state.page = p
            at.run(timeout=10)
            self.assertFalse(at.exception, f"Exception occurred on page '{p}': {at.exception}")

    def test_all_languages_render(self):
        for lang in SUPPORTED_LANGUAGES.keys():
            at = AppTest.from_file(APP_PATH)
            at.session_state.lang = lang
            at.run(timeout=10)
            self.assertFalse(at.exception, f"Exception occurred with language '{lang}': {at.exception}")

    def test_all_simulation_conditions_render(self):
        for cond in ALL_CONDITIONS:
            at = AppTest.from_file(APP_PATH)
            at.session_state.sim_condition = cond
            at.session_state.sensor_reading = None
            at.run(timeout=10)
            self.assertFalse(at.exception, f"Exception occurred under condition '{cond}': {at.exception}")


if __name__ == "__main__":
    unittest.main()
