"""Unit tests for SensorSimulator and telemetry generation."""

import unittest
from services.sensor_simulator import (
    ALL_CONDITIONS,
    CONDITION_DRY,
    CONDITION_HOT,
    CONDITION_NORMAL,
    CONDITION_OFFLINE,
    CONDITION_WET,
    SensorSimulator,
)


class TestSensorSimulator(unittest.TestCase):
    def test_all_conditions_defined(self):
        self.assertEqual(len(ALL_CONDITIONS), 5)
        self.assertIn(CONDITION_NORMAL, ALL_CONDITIONS)
        self.assertIn(CONDITION_DRY, ALL_CONDITIONS)
        self.assertIn(CONDITION_WET, ALL_CONDITIONS)
        self.assertIn(CONDITION_HOT, ALL_CONDITIONS)
        self.assertIn(CONDITION_OFFLINE, ALL_CONDITIONS)

    def test_normal_condition(self):
        reading = SensorSimulator.generate_reading(condition=CONDITION_NORMAL)
        self.assertTrue(reading["is_online"])
        self.assertEqual(reading["condition"], CONDITION_NORMAL)
        self.assertTrue(38.0 <= reading["soil_moisture"] <= 52.0)
        self.assertTrue(22.0 <= reading["temperature"] <= 30.0)
        self.assertTrue(50.0 <= reading["humidity"] <= 75.0)

    def test_dry_condition(self):
        reading = SensorSimulator.generate_reading(condition=CONDITION_DRY)
        self.assertTrue(reading["is_online"])
        self.assertEqual(reading["condition"], CONDITION_DRY)
        # Dry condition should be below the 30% irrigation threshold
        self.assertTrue(reading["soil_moisture"] < 30.0)

    def test_wet_condition(self):
        reading = SensorSimulator.generate_reading(condition=CONDITION_WET)
        self.assertTrue(reading["is_online"])
        self.assertEqual(reading["condition"], CONDITION_WET)
        # Wet condition should be above 60%
        self.assertTrue(reading["soil_moisture"] > 60.0)

    def test_hot_condition(self):
        reading = SensorSimulator.generate_reading(condition=CONDITION_HOT)
        self.assertTrue(reading["is_online"])
        self.assertTrue(reading["temperature"] >= 35.0)

    def test_offline_condition(self):
        reading = SensorSimulator.generate_reading(condition=CONDITION_OFFLINE)
        self.assertFalse(reading["is_online"])
        self.assertEqual(reading["soil_moisture"], 0.0)
        self.assertEqual(reading["temperature"], 0.0)
        self.assertEqual(reading["humidity"], 0.0)
        self.assertEqual(reading["condition"], CONDITION_OFFLINE)

    def test_soil_context_differences(self):
        # Sandy soil drains faster -> lower moisture than clay soil
        reading_sand = SensorSimulator.generate_reading(
            condition=CONDITION_NORMAL,
            farm_context={"soil_type": "Sandy Soil"},
        )
        reading_clay = SensorSimulator.generate_reading(
            condition=CONDITION_NORMAL,
            farm_context={"soil_type": "Clay Soil"},
        )
        self.assertTrue(reading_clay["soil_moisture"] > reading_sand["soil_moisture"])


if __name__ == "__main__":
    unittest.main()
