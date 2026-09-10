"""Tests for KisanSense Home Page SIH-grade UI/UX upgrade.

Covers:
1. Scenario A: Moisture 45%, Temp 27°C, Humidity 62%
   - Farm Health: Good / Optimal
   - Action: No watering needed
   - Climate: Favorable / Normal
   - Clean insights with no active alerts
2. Scenario B: Low soil moisture (e.g. 20%)
   - Farm Health: Action Recommended / Alert
   - Action: Water your crop
   - Direct intelligence grounding
3. Scenario C: High temperature/humidity (e.g. Moisture 72%, Temp 22°C, Humidity 82%)
   - Farm Health: Attention Needed
   - Action: No watering needed + foliage monitoring for fungal risk
4. Absence of raw HTML in UI output
5. Assistant question grounding on Home
"""

import os
import unittest
from streamlit.testing.v1 import AppTest

from services.ai_service import get_ai_response
from services.farm_intelligence import evaluate_farm_intelligence
from services.sensor_service import SensorReading

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))


class TestHomeDashboardRedesign(unittest.TestCase):
    def test_scenario_a_normal_conditions(self):
        """Scenario A: 45% moisture, 27°C temp, 62% humidity."""
        reading = SensorReading(soil_moisture=45.0, temperature=27.0, humidity=62.0, is_online=True)
        intel = evaluate_farm_intelligence(reading, farm_context={"crop": "Tomato"})

        self.assertEqual(intel.primary_severity, "good")
        self.assertFalse(intel.irrigation_status.needs_water)
        self.assertIn("balanced", intel.overall_summary.lower())

        # Test assistant response for Scenario A
        ctx = {
            "crop": "Tomato",
            "soil_moisture": 45.0,
            "temperature": 27.0,
            "humidity": 62.0,
            "sensor_online": True,
            "intelligence": intel,
        }
        water_reply = get_ai_response("Should I water my crop?", context=ctx)
        self.assertIn("not required", water_reply.lower())
        self.assertIn("45%", water_reply)

        farm_reply = get_ai_response("How is my farm?", context=ctx)
        self.assertIn("Optimal", farm_reply)

    def test_scenario_b_low_soil_moisture(self):
        """Scenario B: Low moisture (<30%)."""
        reading = SensorReading(soil_moisture=22.0, temperature=30.0, humidity=50.0, is_online=True)
        intel = evaluate_farm_intelligence(reading, farm_context={"crop": "Tomato"})

        self.assertTrue(intel.irrigation_status.needs_water)
        self.assertIn(intel.primary_severity, ("alert", "critical"))

        ctx = {
            "crop": "Tomato",
            "soil_moisture": 22.0,
            "temperature": 30.0,
            "humidity": 50.0,
            "sensor_online": True,
            "intelligence": intel,
        }
        water_reply = get_ai_response("Should I water my crop?", context=ctx)
        self.assertIn("recommended", water_reply.lower())
        self.assertIn("22%", water_reply)

    def test_scenario_c_high_humidity_wet_soil(self):
        """Scenario C: High moisture (72%), normal temp (22°C), high humidity (82%)."""
        reading = SensorReading(soil_moisture=72.0, temperature=22.0, humidity=82.0, is_online=True)
        intel = evaluate_farm_intelligence(reading, farm_context={"crop": "Tomato"})

        self.assertFalse(intel.irrigation_status.needs_water)
        self.assertEqual(intel.primary_severity, "warning")

        ctx = {
            "crop": "Tomato",
            "soil_moisture": 72.0,
            "temperature": 22.0,
            "humidity": 82.0,
            "sensor_online": True,
            "intelligence": intel,
        }
        # Water question
        water_reply = get_ai_response("Should I water my crop?", context=ctx)
        self.assertIn("72%", water_reply)
        self.assertIn("not required", water_reply.lower())
        self.assertIn("82%", water_reply)
        self.assertIn("fungal", water_reply.lower())

        # Humidity question
        hum_reply = get_ai_response("Why is humidity high?", context=ctx)
        self.assertIn("82%", hum_reply)
        self.assertTrue("fungal" in hum_reply.lower() or "foliage" in hum_reply.lower())

    def test_home_apptest_clean_rendering(self):
        """Verify AppTest renders Home page cleanly across condition changes."""
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.page, "home")

        # Test selecting condition DRY
        at.session_state.sim_condition = "DRY"
        at.session_state.sensor_reading = None
        at.run()
        self.assertFalse(at.exception)

        # Test selecting condition WET
        at.session_state.sim_condition = "WET"
        at.session_state.sensor_reading = None
        at.run()
        self.assertFalse(at.exception)

        # Test selecting condition NORMAL
        at.session_state.sim_condition = "NORMAL"
        at.session_state.sensor_reading = None
        at.run()
        self.assertFalse(at.exception)

    def test_no_raw_html_leaked_in_markdown(self):
        """Verify markdown blocks don't contain escaped <p class='metric-card-description'> text."""
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)
        for md in at.markdown:
            self.assertNotIn('&lt;p class="metric-card-description"&gt;', md.value)
            self.assertNotIn("&lt;div class=", md.value)

    def test_home_plant_health_card_with_and_without_scan(self):
        """Verify Plant Health card appears on Home in both unscanned and scanned states."""
        from services.vision_service import VisionAnalysisResult

        # Case 1: No scan in session state
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)
        scan_btn = [b for b in at.button if b.key == "btn_home_scan_leaf"]
        self.assertEqual(len(scan_btn), 1)

        # Case 2: Scan exists in session state
        at.session_state.latest_vision_result = VisionAnalysisResult(
            success=True,
            is_plant=True,
            healthy=False,
            diagnosis="Early Blight Suspected",
            disease_code="TOMATO_EARLY_BLIGHT",
            crop="Tomato",
            category="fungal",
            confidence=0.85,
            confidence_level="high",
            explanation="Target-like lesions detected on leaf.",
            recommended_action="Prune visibly affected lower foliage.",
            image_quality="good",
            symptoms_detected=["concentric_target_spots"],
            affected_foliage_ratio=0.07,
            treatment_urgency="moderate",
        )
        at.run()
        self.assertFalse(at.exception)
        view_btn = [b for b in at.button if b.key == "btn_home_view_scan"]
        self.assertEqual(len(view_btn), 1)


if __name__ == "__main__":
    unittest.main()
