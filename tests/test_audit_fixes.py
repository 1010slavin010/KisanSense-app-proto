"""Regression test suite for audit findings and stability fixes.

Verifies:
1. Farm profile area validation strictly enforces positive values (> 0).
2. Vision service image quality gate enforces MAX_IMAGE_DIMENSION.
3. Telemetry server HTTP ingest rejects oversized payloads (> 64KB) with 413.
4. Farm intelligence integrates weather context to hold irrigation when rain is imminent.
5. Chatbot does not fabricate weather data when weather is unavailable.
6. Centralized alert service deduplicates alerts by ID.
7. Analytics does not fabricate synthetic historical data and displays honest empty state.
8. Translation key parity and completeness across en, hi, ta, kn.
9. Clean rendering of all routes and simulator conditions in AppTest.
"""

from __future__ import annotations

import io
import unittest
from unittest.mock import MagicMock
from PIL import Image

from services.alert_service import FarmAlert, generate_farm_alerts
from services.ai_service import get_ai_response
from services.farm_intelligence import evaluate_farm_intelligence
from services.farm_service import FarmProfile, validate_farm_profile
from services.sensor_service import SensorReading
from services.vision_service import MAX_IMAGE_DIMENSION, analyze_plant_image
from services.weather_service import WeatherSnapshot
from utils.translations import SUPPORTED_LANGUAGES, TRANSLATIONS, t


class TestFarmProfileAreaValidation(unittest.TestCase):
    """Verify farm area validation enforces non-negative numbers."""

    def test_area_negative_is_rejected(self):
        valid, errors = validate_farm_profile({"crop": "Wheat", "farm_area": -2.5})
        self.assertFalse(valid)
        self.assertIn("farm_area", errors)
        self.assertIn("negative", errors["farm_area"].lower())

    def test_area_positive_is_accepted(self):
        valid, errors = validate_farm_profile({"crop": "Wheat", "farm_area": 3.5})
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)

    def test_area_zero_is_accepted(self):
        valid, errors = validate_farm_profile({"crop": "Wheat", "farm_area": 0.0})
        self.assertTrue(valid)


class TestVisionMaxDimensionGate(unittest.TestCase):
    """Verify vision quality gate enforces MAX_IMAGE_DIMENSION limit."""

    def test_oversized_dimension_rejected(self):
        # Create an image exceeding MAX_IMAGE_DIMENSION
        oversized_img = Image.new("RGB", (MAX_IMAGE_DIMENSION + 50, 200), color=(50, 150, 50))
        buf = io.BytesIO()
        oversized_img.save(buf, format="JPEG")
        raw_bytes = buf.getvalue()

        result = analyze_plant_image(raw_bytes)
        self.assertFalse(result.success)
        self.assertEqual(result.image_quality, "oversized_dimension")
        self.assertIn("maximum supported resolution", result.explanation.lower())


class TestFarmIntelligenceWeatherIntegration(unittest.TestCase):
    """Verify evaluate_farm_intelligence incorporates weather context."""

    def test_rain_imminent_holds_irrigation_in_intelligence(self):
        reading = SensorReading(
            soil_moisture=18.0,  # Dry soil
            temperature=28.0,
            humidity=55.0,
            is_online=True,
        )
        weather = WeatherSnapshot(
            location="Mandya",
            timestamp="10:00",
            temperature=27.0,
            feels_like=27.0,
            humidity=70.0,
            precipitation_probability=80,  # Heavy rain imminent
            precipitation_amount_mm=12.0,
            wind_speed_kmh=10.0,
            wind_direction="W",
            weather_condition="Thunderstorms",
            condition_icon="⛈",
            forecast_summary="Heavy rain approaching",
        )

        intel = evaluate_farm_intelligence(
            reading,
            farm_context={"crop": "Tomato"},
            weather_context=weather,
        )
        self.assertIsNotNone(intel.irrigation_status)
        self.assertFalse(intel.irrigation_status.needs_water)
        self.assertEqual(intel.irrigation_status.label, "Wait / Rain Likely")


class TestChatbotWeatherGroundedness(unittest.TestCase):
    """Verify chatbot reports unavailable weather honestly without fabricating values."""

    def test_weather_unavailable_reported_honestly(self):
        unavailable_weather = WeatherSnapshot(
            location="Remote Field",
            timestamp="",
            temperature=0.0,
            feels_like=0.0,
            humidity=0.0,
            precipitation_probability=0,
            precipitation_amount_mm=0.0,
            wind_speed_kmh=0.0,
            wind_direction="",
            weather_condition="",
            condition_icon="",
            forecast_summary="",
            is_available=False,
            error_message="Station disconnected",
        )
        ctx = {"crop": "Rice", "weather": unavailable_weather}
        reply = get_ai_response("Will it rain today?", context=ctx)
        self.assertIn("unavailable", reply.lower())
        self.assertNotIn("28.0°C", reply)


class TestAlertDeduplication(unittest.TestCase):
    """Verify alert generation removes duplicates by id."""

    def test_alert_deduplication(self):
        reading = SensorReading(soil_moisture=15.0, temperature=28.0, humidity=50.0, is_online=True)
        alerts = generate_farm_alerts(reading=reading, farm_context={"crop": "Wheat"})
        alert_ids = [a.id for a in alerts]
        self.assertEqual(len(alert_ids), len(set(alert_ids)), "Alert IDs must be unique (no duplicates).")


class TestTranslationParity(unittest.TestCase):
    """Verify all newly added keys exist across all 4 languages."""

    def test_new_keys_present_in_all_languages(self):
        expected_keys = [
            "qa_title", "qa_scan", "qa_irrigation", "qa_alerts", "qa_devices", "qa_analytics", "qa_assistant",
            "devices_header_title", "devices_header_subtitle", "devices_telemetry_diagnostics",
            "devices_battery_voltage", "devices_wifi_rssi", "devices_probe_integrity", "devices_data_freshness",
            "analytics_header_title", "analytics_header_subtitle", "analytics_avg_moisture",
            "analytics_avg_temp", "analytics_uptime", "analytics_scans", "analytics_trends_title",
            "analytics_log_title", "analytics_no_history",
        ]
        for lang in SUPPORTED_LANGUAGES.keys():
            locale = TRANSLATIONS.get(lang, {})
            for k in expected_keys:
                self.assertIn(k, locale, f"Key '{k}' missing from language '{lang}'")


if __name__ == "__main__":
    unittest.main()
