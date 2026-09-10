"""Unit tests for KisanSense Weather & Climate Intelligence Service.

Verifies:
- Deterministic simulation of weather snapshots across all agrarian conditions
- Realistic agrarian weather attributes (ET0, solar radiation, precipitation, wind)
- 3-day forecast structure, temperatures, and agrarian advisories
- Offline fallback and demo provenance contract (is_demo=True)
- Location-based baseline modulation
"""

from __future__ import annotations

import unittest

from services.weather_service import (
    WeatherForecastDay,
    WeatherSnapshot,
    get_weather_snapshot,
)


class TestWeatherService(unittest.TestCase):
    def test_default_weather_snapshot(self):
        snap = get_weather_snapshot()
        self.assertIsInstance(snap, WeatherSnapshot)
        self.assertTrue(snap.is_demo)
        self.assertEqual(snap.source, "demo_weather_simulator")
        self.assertIn("Mandya", snap.location)
        self.assertGreater(snap.temperature_c, 0)
        self.assertGreater(snap.humidity, 0)
        self.assertGreaterEqual(snap.rain_probability, 0)
        self.assertLessEqual(snap.rain_probability, 100)
        self.assertGreaterEqual(snap.evapotranspiration_mm, 0)
        self.assertGreaterEqual(snap.solar_irradiance_w_m2, 0)
        self.assertEqual(len(snap.forecast), 3)

    def test_condition_modulation_wet_and_waterlogging(self):
        wet_snap = get_weather_snapshot(condition_hint="WET")
        self.assertGreaterEqual(wet_snap.rain_probability, 60)
        self.assertGreater(wet_snap.precipitation_mm, 0)
        self.assertIn(wet_snap.condition, ("Showers", "Moderate Rain", "Heavy Rain", "Thunderstorms"))

        waterlogged_snap = get_weather_snapshot(condition_hint="WATERLOGGING")
        self.assertGreaterEqual(waterlogged_snap.rain_probability, 70)
        self.assertGreater(waterlogged_snap.precipitation_mm, 5.0)

    def test_condition_modulation_hot_and_dry(self):
        hot_snap = get_weather_snapshot(condition_hint="HOT")
        self.assertGreaterEqual(hot_snap.temperature_c, 34.0)
        self.assertGreaterEqual(hot_snap.evapotranspiration_mm, 5.0)

        dry_snap = get_weather_snapshot(condition_hint="DRY")
        self.assertLessEqual(dry_snap.rain_probability, 25)
        self.assertEqual(dry_snap.precipitation_mm, 0.0)

        heat_drought = get_weather_snapshot(condition_hint="HEAT_DROUGHT")
        self.assertGreaterEqual(heat_drought.temperature_c, 36.0)
        self.assertLessEqual(heat_drought.humidity, 45.0)

    def test_condition_modulation_humid_heat(self):
        humid_heat = get_weather_snapshot(condition_hint="HUMID_HEAT")
        self.assertGreaterEqual(humid_heat.temperature_c, 32.0)
        self.assertGreaterEqual(humid_heat.humidity, 75.0)

    def test_forecast_structure_and_advisories(self):
        snap = get_weather_snapshot(location="Punjab, Ludhiana", condition_hint="NORMAL")
        self.assertEqual(len(snap.forecast), 3)
        for day in snap.forecast:
            self.assertIsInstance(day, WeatherForecastDay)
            self.assertTrue(len(day.date_str) > 0)
            self.assertTrue(len(day.condition) > 0)
            self.assertLessEqual(day.temp_min_c, day.temp_max_c)
            self.assertGreaterEqual(day.rain_prob, 0)
            self.assertLessEqual(day.rain_prob, 100)
            self.assertTrue(len(day.agrarian_advisory) > 0)

    def test_location_customization(self):
        loc = "Shimla, Himachal Pradesh"
        snap = get_weather_snapshot(location=loc, condition_hint="NORMAL")
        self.assertEqual(snap.location, loc)
        # Shimla is cooler than baseline Mandya
        mandya_snap = get_weather_snapshot(location="Mandya, Karnataka", condition_hint="NORMAL")
        self.assertLess(snap.temperature_c, mandya_snap.temperature_c)

    def test_to_dict_conversion(self):
        snap = get_weather_snapshot()
        d = snap.to_dict()
        self.assertEqual(d["location"], snap.location)
        self.assertEqual(d["temperature_c"], snap.temperature_c)
        self.assertEqual(len(d["forecast"]), 3)
        self.assertTrue(d["is_demo"])


if __name__ == "__main__":
    unittest.main()
