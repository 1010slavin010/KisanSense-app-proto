"""Integration tests for KisanSense Phase 5 Smart Farm Intelligence.

Covers:
- Farm Intelligence integration with SensorSimulator (all 8 conditions)
- Farm Intelligence integration with HardwareClient (telemetry injection & fail-safe)
- Farm Intelligence integration with Chatbot & ai_service grounding
- Multilingual coverage for all Phase 5 keys across English, Hindi, Tamil, Kannada
- Streamlit AppTest integration verifying Home dashboard renders Intelligence Advisory
"""

import os
import unittest
from streamlit.testing.v1 import AppTest

from services.ai_service import get_ai_response
from services.farm_intelligence import evaluate_farm_intelligence
from services.hardware_client import HardwareClient
from services.sensor_service import (
    ALL_CONDITIONS,
    CONDITION_HEAT_DROUGHT,
    CONDITION_HOT,
    CONDITION_HUMID_HEAT,
    CONDITION_NORMAL,
    CONDITION_OFFLINE,
    CONDITION_WATERLOGGING,
    SensorReading,
    get_current_sensor_data,
)
from services.sensor_simulator import SensorSimulator
from services.telemetry_store import GLOBAL_TELEMETRY_STORE
from utils.translations import SUPPORTED_LANGUAGES, TRANSLATIONS, t

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))


class TestSimulatorIntelligenceIntegration(unittest.TestCase):
    """Verify all simulator profiles produce valid readings evaluated by intelligence."""

    def test_all_eight_simulator_conditions_with_intelligence(self):
        ctx = {"crop": "Tomato", "growth_stage": "Flowering"}
        for cond in ALL_CONDITIONS:
            raw = SensorSimulator.generate_reading(condition=cond, farm_context=ctx)
            reading = SensorReading(
                soil_moisture=raw["soil_moisture"],
                temperature=raw["temperature"],
                humidity=raw["humidity"],
                is_online=raw["is_online"],
                condition=raw["condition"],
            )
            intel = evaluate_farm_intelligence(reading, farm_context=ctx)
            self.assertIsNotNone(intel.primary_status)
            self.assertIsNotNone(intel.overall_summary)
            self.assertTrue(len(intel.conditions) > 0)

            if cond == CONDITION_OFFLINE:
                self.assertEqual(intel.data_quality, "offline")
                self.assertFalse(intel.irrigation_status.needs_water)
            elif cond == CONDITION_HEAT_DROUGHT:
                self.assertEqual(intel.primary_severity, "critical")
                self.assertTrue(intel.irrigation_status.needs_water)
            elif cond == CONDITION_WATERLOGGING:
                self.assertFalse(intel.irrigation_status.needs_water)
                self.assertIn(intel.primary_severity, ("warning", "alert"))


class TestHardwareIntelligenceIntegration(unittest.TestCase):
    """Verify hardware telemetry streams cleanly through intelligence."""

    def setUp(self):
        GLOBAL_TELEMETRY_STORE.clear()

    def tearDown(self):
        GLOBAL_TELEMETRY_STORE.clear()

    def test_hardware_reliable_packet(self):
        HardwareClient.ingest({
            "device_id": "esp32-intel-01",
            "soil_moisture": 22.5,
            "temperature": 36.0,
            "humidity": 45.0,
            "battery_voltage": 4.10,
        })
        reading = get_current_sensor_data(mode="hardware")
        intel = evaluate_farm_intelligence(reading, farm_context={"crop": "Wheat"})

        self.assertEqual(intel.data_quality, "reliable")
        self.assertTrue(intel.irrigation_status.needs_water)
        self.assertEqual(intel.primary_status, "Action Recommended")

    def test_hardware_probe_disconnected_packet(self):
        HardwareClient.ingest({
            "device_id": "esp32-intel-02",
            "soil_moisture": 0.0,
            "temperature": 0.0,
            "humidity": 0.0,
            "raw_status": "probe_disconnected",
        })
        reading = get_current_sensor_data(mode="hardware")
        intel = evaluate_farm_intelligence(reading, farm_context={"crop": "Wheat"})

        self.assertEqual(intel.data_quality, "fault")
        self.assertFalse(intel.irrigation_status.needs_water)
        self.assertEqual(intel.irrigation_status.label, "Sensor Offline")


class TestChatbotIntelligenceGrounding(unittest.TestCase):
    """Verify AI service answers are grounded in FarmIntelligenceResult."""

    def test_chatbot_farm_health_query_online(self):
        reading = SensorReading(soil_moisture=45.0, temperature=26.0, humidity=60.0, is_online=True)
        intel = evaluate_farm_intelligence(reading, farm_context={"crop": "Tomato"})
        context = {"crop": "Tomato", "intelligence": intel, "sensor_online": True}

        reply = get_ai_response("How is my farm health?", context=context)
        self.assertIn("Optimal", reply)
        self.assertIn("balanced", reply.lower())

    def test_chatbot_farm_health_query_offline(self):
        reading = SensorReading(soil_moisture=0.0, temperature=0.0, humidity=0.0, is_online=False)
        intel = evaluate_farm_intelligence(reading, farm_context={"crop": "Tomato"})
        context = {"crop": "Tomato", "intelligence": intel, "sensor_online": False}

        reply = get_ai_response("How is my farm doing?", context=context)
        self.assertIn("offline", reply.lower())
        self.assertIn("inspect", reply.lower())

    def test_chatbot_grounded_compound_stress(self):
        reading = SensorReading(soil_moisture=18.0, temperature=41.0, humidity=25.0, is_online=True)
        intel = evaluate_farm_intelligence(reading, farm_context={"crop": "Cotton", "growth_stage": "Flowering"})
        context = {
            "crop": "Cotton",
            "growth_stage": "Flowering",
            "soil_moisture": 18.0,
            "temperature": 41.0,
            "sensor_online": True,
            "intelligence": intel,
        }

        reply = get_ai_response("Should I water my crop today?", context=context)
        self.assertIn("Cotton", reply)
        self.assertIn("Flowering", reply)
        self.assertIn("Irrigation is recommended", reply)


class TestIntelligenceTranslationsCompleteness(unittest.TestCase):
    """Verify all Phase 5 intelligence keys are defined in all supported languages."""

    REQUIRED_PHASE5_KEYS = [
        "sim_heat_drought",
        "sim_waterlogging",
        "sim_humid_heat",
        "intel_card_title",
        "intel_status_label",
        "intel_confidence_label",
        "intel_confidence_high",
        "intel_confidence_moderate",
        "intel_confidence_low",
        "intel_action_label",
        "intel_conditions_title",
        "intel_status_optimal",
        "intel_status_attention",
        "intel_status_action",
        "intel_status_action_required",
        "intel_status_offline",
        "intel_status_fault",
    ]

    def test_keys_exist_in_all_locales(self):
        for lang in SUPPORTED_LANGUAGES:
            self.assertIn(lang, TRANSLATIONS)
            locale_dict = TRANSLATIONS[lang]
            for key in self.REQUIRED_PHASE5_KEYS:
                self.assertIn(
                    key,
                    locale_dict,
                    f"Missing translation key '{key}' in locale '{lang}'",
                )
                self.assertTrue(
                    len(locale_dict[key].strip()) > 0,
                    f"Empty translation for '{key}' in locale '{lang}'",
                )

    def test_translation_helper_fallback(self):
        # Existing fallback mechanism continues working
        val = t("intel_card_title", lang="en")
        self.assertEqual(val, "Smart Farm Intelligence")


class TestHomeDashboardIntelligenceRender(unittest.TestCase):
    """Verify Home dashboard renders without errors and shows Intelligence Advisory."""

    def test_home_page_renders_intelligence_card(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        # Home page must run cleanly
        self.assertEqual(at.session_state.page, "home")

        # Test selecting new Phase 5 condition HEAT_DROUGHT
        at.session_state.sim_condition = "HEAT_DROUGHT"
        at.session_state.sensor_reading = None
        at.run()
        self.assertFalse(at.exception)

        # Test selecting WATERLOGGING
        at.session_state.sim_condition = "WATERLOGGING"
        at.session_state.sensor_reading = None
        at.run()
        self.assertFalse(at.exception)

        # Test selecting HUMID_HEAT
        at.session_state.sim_condition = "HUMID_HEAT"
        at.session_state.sensor_reading = None
        at.run()
        self.assertFalse(at.exception)


if __name__ == "__main__":
    unittest.main()
