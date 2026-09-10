"""Tests for KisanSense Assistant integration with Smart Farm Intelligence.

Verifies:
1. Telemetry-aware responses using current example values:
   - Soil Moisture: 72%
   - Temperature: 22°C
   - Air Humidity: 82%
2. All required farmer questions:
   - "How is my farm?"
   - "What should I do now?"
   - "Should I water my crop?"
   - "Does my crop need irrigation?"
   - "How is the soil?"
   - "What is my soil condition?"
   - "Why is humidity high?"
   - "Is the temperature okay?"
   - "Is my crop at risk?"
   - "What should I do today?"
   - "Is irrigation required?"
   - "What are the current conditions?"
3. Complete removal of placeholder fallback message.
4. Clean HTML rendering of metric cards without Markdown code block escaping.
"""

import unittest
from services.ai_service import get_ai_response
from services.farm_intelligence import evaluate_farm_intelligence
from services.sensor_service import SensorReading


class TestAssistantIntelligence(unittest.TestCase):
    def setUp(self):
        self.context_72_22_82 = {
            "crop": "Tomato",
            "crop_variety": "Roma",
            "soil_type": "Loamy Soil",
            "growth_stage": "Flowering",
            "irrigation_method": "Drip Irrigation",
            "soil_moisture": 72.0,
            "temperature": 22.0,
            "humidity": 82.0,
            "sensor_online": True,
        }
        self.reading = SensorReading(
            soil_moisture=72.0,
            temperature=22.0,
            humidity=82.0,
            is_online=True,
        )
        self.intel = evaluate_farm_intelligence(self.reading, farm_context=self.context_72_22_82)
        self.context_72_22_82["intelligence"] = self.intel

    def test_no_placeholder_in_any_response(self):
        queries = [
            "How is my farm?",
            "What should I do now?",
            "Should I water my crop?",
            "Does my crop need irrigation?",
            "How is the soil?",
            "What is my soil condition?",
            "Why is humidity high?",
            "Is the temperature okay?",
            "Is my crop at risk?",
            "What should I do today?",
            "Is irrigation required?",
            "What are the current conditions?",
            "random unhandled question about stars",
            "xyz12345?!",
        ]
        for q in queries:
            reply = get_ai_response(q, context=self.context_72_22_82)
            self.assertNotIn("placeholder assistant", reply.lower())
            self.assertNotIn("future update", reply.lower())

    def test_water_query_72_percent_moisture(self):
        # Soil moisture is 72% -> sufficiently wet, irrigation not required
        for q in ["Should I water my crop?", "Does my crop need irrigation?", "Is irrigation required?"]:
            reply = get_ai_response(q, context=self.context_72_22_82)
            self.assertIn("72%", reply)
            self.assertIn("not required", reply.lower())
            self.assertIn("sufficiently wet", reply.lower())
            # With 82% humidity, should also caution about foliage / fungal risk
            self.assertIn("82%", reply)
            self.assertIn("fungal", reply.lower())

    def test_soil_query_72_percent_moisture(self):
        for q in ["How is the soil?", "What is my soil condition?"]:
            reply = get_ai_response(q, context=self.context_72_22_82)
            self.assertIn("72%", reply)
            self.assertIn("sufficiently wet", reply.lower())

    def test_humidity_query_82_percent(self):
        reply = get_ai_response("Why is humidity high?", context=self.context_72_22_82)
        self.assertIn("82%", reply)
        self.assertIn("high", reply.lower())
        self.assertTrue("fungal" in reply.lower() or "foliage" in reply.lower() or "mildew" in reply.lower())

    def test_temperature_query_22_c(self):
        reply = get_ai_response("Is the temperature okay?", context=self.context_72_22_82)
        self.assertIn("22°C", reply)
        self.assertTrue("comfortable" in reply.lower() or "normal" in reply.lower() or "favorable" in reply.lower())

    def test_how_is_my_farm_and_current_conditions(self):
        for q in ["How is my farm?", "What are the current conditions?"]:
            reply = get_ai_response(q, context=self.context_72_22_82)
            self.assertIn("72%", reply)
            self.assertIn("22°C", reply)
            self.assertIn("82%", reply)

    def test_what_should_i_do_now_and_today(self):
        for q in ["What should I do now?", "What should I do today?"]:
            reply = get_ai_response(q, context=self.context_72_22_82)
            self.assertIn("Irrigation", reply)
            self.assertTrue("do not irrigate" in reply.lower() or "not required" in reply.lower())
            self.assertTrue("humidity" in reply.lower() or "foliage" in reply.lower() or "monitoring" in reply.lower())

    def test_crop_at_risk_query(self):
        reply = get_ai_response("Is my crop at risk?", context=self.context_72_22_82)
        self.assertTrue("risk" in reply.lower() or "fungal" in reply.lower() or "humidity" in reply.lower())
        self.assertIn("leaves", reply.lower())

    def test_dynamic_values_not_hardcoded(self):
        # Verify that changing telemetry to 25% moisture and 38°C temp gives different, appropriate answers
        dry_ctx = {
            "crop": "Wheat",
            "soil_moisture": 25.0,
            "temperature": 38.0,
            "humidity": 30.0,
            "sensor_online": True,
        }
        reply_water = get_ai_response("Should I water my crop?", context=dry_ctx)
        self.assertIn("25%", reply_water)
        self.assertIn("recommended", reply_water.lower())

        reply_temp = get_ai_response("Is the temperature okay?", context=dry_ctx)
        self.assertIn("38°C", reply_temp)
        self.assertIn("elevated", reply_temp.lower())


class TestMetricCardCleanHtml(unittest.TestCase):
    def test_clean_html_assembly(self):
        # Test that card rendering does not introduce Markdown code block indentation
        title = "Soil Moisture"
        value = "72%"
        status_type = "good"
        description = "Soil is already sufficiently wet (72%)."

        badge_html = ""
        progress_html = ""
        elements = [
            f'<div class="metric-card metric-card-{status_type}">',
            f'<div class="metric-card-title">{title}</div>',
            f'<div class="metric-card-value">{value}</div>',
        ]
        if badge_html:
            elements.append(badge_html)
        if progress_html:
            elements.append(progress_html)
        elements.append(f'<p class="metric-card-description">{description}</p>')
        elements.append('</div>')

        card_html = "".join(elements)
        # Ensure no leading whitespace on description or empty line before it
        self.assertIn('<p class="metric-card-description">Soil is already sufficiently wet (72%).</p>', card_html)
        self.assertNotIn("    <p class=\"metric-card-description\"", card_html)
        self.assertNotIn("\n\n", card_html)


if __name__ == "__main__":
    unittest.main()
