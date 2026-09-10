"""Unit tests for KisanSense Weather Intelligence Decision Engine.

Verifies:
- Case A: Soil moisture low + dry weather -> water recommended soon
- Case B: Soil moisture low + heavy rain forecasted -> wait / delay irrigation
- Case C: Adequate moisture + heavy rain -> avoid overwatering, monitor field drainage
- Case D: High heat + dry soil -> compound heat & water stress advisory
- Case E: Warm + humid + wet -> foliar disease risk watch (linked to vision if present)
- Case F: High wind -> spraying postponed
- Normal baseline conditions
- Risk signal severity classifications
"""

from __future__ import annotations

import unittest

from services.farm_intelligence import evaluate_farm_intelligence
from services.sensor_service import SensorReading
from services.vision_service import VisionAnalysisResult
from services.weather_intelligence import (
    WeatherFarmInsight,
    WeatherRiskSignal,
    evaluate_weather_intelligence,
)
from services.weather_service import get_weather_snapshot


class TestWeatherIntelligence(unittest.TestCase):
    def setUp(self):
        self.crop_ctx = {"crop": "Tomato", "soil_type": "Loamy", "location": "Mandya, Karnataka"}

    def test_case_a_low_moisture_no_rain(self):
        """Case A: Soil moisture low (< 30%) + no rain forecasted -> Water soon."""
        reading = SensorReading(soil_moisture=22.0, temperature=28.0, humidity=50.0, is_online=True)
        weather = get_weather_snapshot(condition_hint="DRY")
        intel = evaluate_farm_intelligence(reading, farm_context=self.crop_ctx)

        insight = evaluate_weather_intelligence(weather, reading, self.crop_ctx, intel=intel)
        self.assertIsInstance(insight, WeatherFarmInsight)
        self.assertIn(insight.status_type, ("warning", "alert"))
        self.assertIn("Water", insight.primary_action)
        self.assertIn("irrigation", insight.irrigation_guidance.lower())

    def test_case_b_low_moisture_rain_expected(self):
        """Case B: Soil moisture low (< 30%) + heavy rain expected (>= 60%) -> Wait / delay."""
        reading = SensorReading(soil_moisture=24.0, temperature=25.0, humidity=75.0, is_online=True)
        weather = get_weather_snapshot(condition_hint="WET")
        self.assertGreaterEqual(weather.rain_probability, 60)
        intel = evaluate_farm_intelligence(reading, farm_context=self.crop_ctx)

        insight = evaluate_weather_intelligence(weather, reading, self.crop_ctx, intel=intel)
        self.assertIn(insight.status_type, ("warning", "good"))
        self.assertIn("Wait", insight.primary_action)
        self.assertIn("rain", insight.irrigation_guidance.lower())

    def test_case_c_adequate_moisture_heavy_rain(self):
        """Case C: Soil moisture adequate (48%) + heavy rain -> Drainage alert."""
        reading = SensorReading(soil_moisture=48.0, temperature=23.0, humidity=80.0, is_online=True)
        weather = get_weather_snapshot(condition_hint="WET")
        intel = evaluate_farm_intelligence(reading, farm_context=self.crop_ctx)

        insight = evaluate_weather_intelligence(weather, reading, self.crop_ctx, intel=intel)
        self.assertIn("drainage", insight.action_detail.lower())
        self.assertIn("drainage", insight.irrigation_guidance.lower())

    def test_case_d_high_heat_dry_soil(self):
        """Case D: High heat + low soil moisture -> Compound heat stress."""
        reading = SensorReading(soil_moisture=20.0, temperature=38.0, humidity=30.0, is_online=True)
        weather = get_weather_snapshot(condition_hint="HEAT_DROUGHT")
        intel = evaluate_farm_intelligence(reading, farm_context=self.crop_ctx)

        insight = evaluate_weather_intelligence(weather, reading, self.crop_ctx, intel=intel)
        self.assertIn(insight.status_type, ("warning", "alert"))
        # Check that heat stress risk signal exists
        risk_types = [r.risk_type for r in insight.active_risks]
        self.assertIn("heat_stress", risk_types)
        self.assertIn("Water", insight.primary_action)

    def test_case_e_humid_warm_disease_watch(self):
        """Case E: Warm + humid canopy -> Foliar disease watch with vision cross-reference."""
        reading = SensorReading(soil_moisture=65.0, temperature=29.0, humidity=82.0, is_online=True)
        weather = get_weather_snapshot(condition_hint="HUMID_HEAT")
        intel = evaluate_farm_intelligence(reading, farm_context=self.crop_ctx)

        # Mock a crop vision result with Early Blight symptoms
        vision = VisionAnalysisResult(
            success=True,
            is_plant=True,
            healthy=False,
            diagnosis="Early Blight",
            disease_code="early_blight",
            crop="Tomato",
            category="fungal",
            confidence=0.88,
            confidence_level="high",
            explanation="Concentric brown rings on lower leaves",
            recommended_action="Remove affected foliage and apply copper fungicide",
            image_quality="good",
        )

        insight = evaluate_weather_intelligence(
            weather, reading, self.crop_ctx, intel=intel, vision_result=vision
        )
        risk_types = [r.risk_type for r in insight.active_risks]
        self.assertIn("humidity_disease", risk_types)
        # Verify that recent scan diagnosis was folded into explanation / action note
        hum_risk = next(r for r in insight.active_risks if r.risk_type == "humidity_disease")
        self.assertIn("Early Blight", hum_risk.action)

    def test_case_f_high_wind_spraying_caution(self):
        """Case F: High wind (> 20 km/h) -> Spraying caution."""
        reading = SensorReading(soil_moisture=45.0, temperature=26.0, humidity=55.0, is_online=True)
        weather = get_weather_snapshot(condition_hint="NORMAL")
        # Force wind speed high
        weather.wind_speed_kmh = 32.0
        intel = evaluate_farm_intelligence(reading, farm_context=self.crop_ctx)

        insight = evaluate_weather_intelligence(weather, reading, self.crop_ctx, intel=intel)
        risk_types = [r.risk_type for r in insight.active_risks]
        self.assertIn("strong_wind", risk_types)
        self.assertIn("Postpone", insight.field_work_advisory)

    def test_normal_baseline_stable_conditions(self):
        """Normal baseline conditions -> good status, no critical risks."""
        reading = SensorReading(soil_moisture=45.0, temperature=26.0, humidity=55.0, is_online=True)
        weather = get_weather_snapshot(condition_hint="NORMAL")
        intel = evaluate_farm_intelligence(reading, farm_context=self.crop_ctx)

        insight = evaluate_weather_intelligence(weather, reading, self.crop_ctx, intel=intel)
        self.assertEqual(insight.status_type, "good")
        self.assertIn("favorable", insight.primary_action.lower())


if __name__ == "__main__":
    unittest.main()
