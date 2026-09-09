"""Tests for ai_service and irrigation_service with and without farm context."""

import unittest
from services.ai_service import get_ai_response
from services.irrigation_service import IrrigationStatus, get_irrigation_status


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
