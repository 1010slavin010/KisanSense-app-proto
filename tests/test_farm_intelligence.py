"""Unit tests for services.farm_intelligence.

Covers:
- Safety Gate (offline, fault, stale, invalid out-of-bounds, battery low)
- Soil moisture boundary conditions (19.9, 20.0, 29.9, 30.0, 60.0, 60.1, 75.0, 75.1)
- Temperature boundary conditions (35.0, 35.1, 40.0, 40.1)
- Humidity boundary conditions (34.9, 35.0, 75.0, 80.0, 80.1)
- Compound condition interactions (Heat+Drought, Wet+Humid, Heat+Humid)
- Farm profile context modulation (Crop, Stage, Soil, Irrigation method)
- Severity hierarchy and deterministic ordering
- Non-fabrication and missing context graceful degradation
"""

import unittest
from services.farm_intelligence import (
    FarmCondition,
    FarmIntelligenceResult,
    evaluate_farm_intelligence,
)
from services.sensor_service import SensorReading


class TestFarmIntelligenceSafety(unittest.TestCase):
    """Verify the Safety Gate behaves fail-safe under all anomaly conditions."""

    def test_sensor_offline_suppresses_agronomy_and_fails_safe(self):
        reading = SensorReading(soil_moisture=0.0, temperature=0.0, humidity=0.0, is_online=False)
        result = evaluate_farm_intelligence(reading)

        self.assertIsInstance(result, FarmIntelligenceResult)
        self.assertEqual(result.data_quality, "offline")
        self.assertEqual(result.primary_status, "Sensor Offline")
        self.assertEqual(result.primary_severity, "alert")
        # Irrigation fail-safe
        self.assertIsNotNone(result.irrigation_status)
        self.assertFalse(result.irrigation_status.needs_water)
        self.assertEqual(result.irrigation_status.label, "Sensor Offline")
        # Agronomic conditions are suppressed, only safety condition emitted
        self.assertEqual(len(result.conditions), 1)
        self.assertEqual(result.conditions[0].code, "SENSOR_OFFLINE")
        self.assertIn("unavailable", result.overall_summary.lower())

    def test_probe_disconnected_fault(self):
        reading = SensorReading(
            soil_moisture=0.0,
            temperature=25.0,
            humidity=50.0,
            is_online=True,
            raw_status="probe_disconnected",
        )
        result = evaluate_farm_intelligence(reading)

        self.assertEqual(result.data_quality, "fault")
        self.assertEqual(result.primary_status, "Hardware Fault Detected")
        self.assertEqual(result.primary_severity, "critical")
        self.assertFalse(result.irrigation_status.needs_water)
        self.assertEqual(result.conditions[0].code, "HARDWARE_FAULT")

    def test_hardware_fault_generic(self):
        reading = SensorReading(
            soil_moisture=10.0,
            temperature=30.0,
            humidity=40.0,
            is_online=True,
            raw_status="sensor_fault",
        )
        result = evaluate_farm_intelligence(reading)

        self.assertEqual(result.data_quality, "fault")
        self.assertFalse(result.irrigation_status.needs_water)

    def test_stale_telemetry_status(self):
        reading = SensorReading(
            soil_moisture=20.0,
            temperature=28.0,
            humidity=50.0,
            is_online=True,
            raw_status="stale_or_offline",
        )
        result = evaluate_farm_intelligence(reading)

        self.assertEqual(result.data_quality, "stale")
        self.assertEqual(result.primary_status, "Stale Telemetry")
        self.assertEqual(result.primary_severity, "warning")
        self.assertFalse(result.irrigation_status.needs_water)

    def test_invalid_telemetry_out_of_bounds(self):
        # Soil moisture > 100%
        reading_sm = SensorReading(soil_moisture=110.0, temperature=25.0, humidity=50.0, is_online=True)
        res_sm = evaluate_farm_intelligence(reading_sm)
        self.assertEqual(res_sm.data_quality, "invalid")
        self.assertEqual(res_sm.primary_status, "Invalid Telemetry")

        # Negative soil moisture
        reading_sm_neg = SensorReading(soil_moisture=-5.0, temperature=25.0, humidity=50.0, is_online=True)
        res_sm_neg = evaluate_farm_intelligence(reading_sm_neg)
        self.assertEqual(res_sm_neg.data_quality, "invalid")

        # Temperature out of bounds (> 65°C)
        reading_temp = SensorReading(soil_moisture=45.0, temperature=75.0, humidity=50.0, is_online=True)
        res_temp = evaluate_farm_intelligence(reading_temp)
        self.assertEqual(res_temp.data_quality, "invalid")

        # Humidity out of bounds (> 100%)
        reading_hum = SensorReading(soil_moisture=45.0, temperature=25.0, humidity=105.0, is_online=True)
        res_hum = evaluate_farm_intelligence(reading_hum)
        self.assertEqual(res_hum.data_quality, "invalid")

    def test_low_battery_warning(self):
        reading = SensorReading(
            soil_moisture=45.0,
            temperature=25.0,
            humidity=50.0,
            is_online=True,
            battery_voltage=3.25,
        )
        result = evaluate_farm_intelligence(reading)
        self.assertEqual(result.data_quality, "reliable")
        codes = [c.code for c in result.conditions]
        self.assertIn("BATTERY_LOW", codes)


class TestSoilMoistureBoundaries(unittest.TestCase):
    """Verify precise soil moisture thresholds."""

    def test_moisture_19_9_severe_dryness(self):
        reading = SensorReading(soil_moisture=19.9, temperature=26.0, humidity=55.0)
        res = evaluate_farm_intelligence(reading)
        codes = [c.code for c in res.conditions]
        self.assertIn("SEVERE_DRYNESS", codes)
        self.assertTrue(res.irrigation_status.needs_water)

    def test_moisture_20_0_moderate_dryness(self):
        reading = SensorReading(soil_moisture=20.0, temperature=26.0, humidity=55.0)
        res = evaluate_farm_intelligence(reading)
        codes = [c.code for c in res.conditions]
        self.assertIn("MODERATE_DRYNESS", codes)
        self.assertTrue(res.irrigation_status.needs_water)

    def test_moisture_29_9_moderate_dryness(self):
        reading = SensorReading(soil_moisture=29.9, temperature=26.0, humidity=55.0)
        res = evaluate_farm_intelligence(reading)
        codes = [c.code for c in res.conditions]
        self.assertIn("MODERATE_DRYNESS", codes)
        self.assertTrue(res.irrigation_status.needs_water)

    def test_moisture_30_0_adequate_moisture(self):
        reading = SensorReading(soil_moisture=30.0, temperature=26.0, humidity=55.0)
        res = evaluate_farm_intelligence(reading)
        codes = [c.code for c in res.conditions]
        self.assertIn("ADEQUATE_MOISTURE", codes)
        self.assertFalse(res.irrigation_status.needs_water)

    def test_moisture_60_0_adequate_moisture(self):
        reading = SensorReading(soil_moisture=60.0, temperature=26.0, humidity=55.0)
        res = evaluate_farm_intelligence(reading)
        codes = [c.code for c in res.conditions]
        self.assertIn("ADEQUATE_MOISTURE", codes)
        self.assertFalse(res.irrigation_status.needs_water)

    def test_moisture_60_1_excessive_moisture(self):
        reading = SensorReading(soil_moisture=60.1, temperature=26.0, humidity=55.0)
        res = evaluate_farm_intelligence(reading)
        codes = [c.code for c in res.conditions]
        self.assertIn("EXCESSIVE_MOISTURE", codes)
        self.assertFalse(res.irrigation_status.needs_water)

    def test_moisture_75_0_excessive_moisture(self):
        reading = SensorReading(soil_moisture=75.0, temperature=26.0, humidity=55.0)
        res = evaluate_farm_intelligence(reading)
        codes = [c.code for c in res.conditions]
        self.assertIn("EXCESSIVE_MOISTURE", codes)

    def test_moisture_75_1_waterlogging_risk(self):
        reading = SensorReading(soil_moisture=75.1, temperature=26.0, humidity=55.0)
        res = evaluate_farm_intelligence(reading)
        codes = [c.code for c in res.conditions]
        self.assertIn("WATERLOGGING_RISK", codes)


class TestTemperatureBoundaries(unittest.TestCase):
    """Verify temperature boundaries."""

    def test_temp_35_0_normal(self):
        reading = SensorReading(soil_moisture=45.0, temperature=35.0, humidity=55.0)
        res = evaluate_farm_intelligence(reading)
        codes = [c.code for c in res.conditions]
        self.assertIn("TEMP_NORMAL", codes)

    def test_temp_35_1_elevated_heat(self):
        reading = SensorReading(soil_moisture=45.0, temperature=35.1, humidity=55.0)
        res = evaluate_farm_intelligence(reading)
        codes = [c.code for c in res.conditions]
        self.assertIn("ELEVATED_HEAT", codes)

    def test_temp_40_0_elevated_heat(self):
        reading = SensorReading(soil_moisture=45.0, temperature=40.0, humidity=55.0)
        res = evaluate_farm_intelligence(reading)
        codes = [c.code for c in res.conditions]
        self.assertIn("ELEVATED_HEAT", codes)

    def test_temp_40_1_severe_heat_risk(self):
        reading = SensorReading(soil_moisture=45.0, temperature=40.1, humidity=55.0)
        res = evaluate_farm_intelligence(reading)
        codes = [c.code for c in res.conditions]
        self.assertIn("SEVERE_HEAT_RISK", codes)


class TestHumidityBoundaries(unittest.TestCase):
    """Verify humidity boundaries."""

    def test_humidity_34_9_dry_air(self):
        reading = SensorReading(soil_moisture=45.0, temperature=25.0, humidity=34.9)
        res = evaluate_farm_intelligence(reading)
        codes = [c.code for c in res.conditions]
        self.assertIn("DRY_AIR", codes)

    def test_humidity_35_0_acceptable(self):
        reading = SensorReading(soil_moisture=45.0, temperature=25.0, humidity=35.0)
        res = evaluate_farm_intelligence(reading)
        codes = [c.code for c in res.conditions]
        self.assertTrue("HUMIDITY_ACCEPTABLE" in codes or "HUMIDITY_NORMAL" in codes)

    def test_humidity_75_0_normal(self):
        reading = SensorReading(soil_moisture=45.0, temperature=25.0, humidity=75.0)
        res = evaluate_farm_intelligence(reading)
        codes = [c.code for c in res.conditions]
        self.assertIn("HUMIDITY_NORMAL", codes)

    def test_humidity_80_0_acceptable(self):
        reading = SensorReading(soil_moisture=45.0, temperature=25.0, humidity=80.0)
        res = evaluate_farm_intelligence(reading)
        codes = [c.code for c in res.conditions]
        self.assertNotIn("HIGH_HUMIDITY", codes)

    def test_humidity_80_1_high_humidity(self):
        reading = SensorReading(soil_moisture=45.0, temperature=25.0, humidity=80.1)
        res = evaluate_farm_intelligence(reading)
        codes = [c.code for c in res.conditions]
        self.assertIn("HIGH_HUMIDITY", codes)


class TestCompoundConditions(unittest.TestCase):
    """Verify compound environmental conditions synthesis."""

    def test_compound_heat_and_drought(self):
        # Soil moisture 22% (<30%) and Temperature 38°C (>35°C)
        reading = SensorReading(soil_moisture=22.0, temperature=38.0, humidity=30.0)
        res = evaluate_farm_intelligence(reading)
        codes = [c.code for c in res.conditions]
        self.assertIn("COMPOUND_HEAT_DROUGHT", codes)
        self.assertTrue(res.irrigation_status.needs_water)

    def test_compound_wet_soil_and_high_humidity(self):
        # Soil moisture 72% (>60%) and Humidity 85% (>80%)
        reading = SensorReading(soil_moisture=72.0, temperature=24.0, humidity=85.0)
        res = evaluate_farm_intelligence(reading)
        codes = [c.code for c in res.conditions]
        self.assertIn("COMPOUND_WET_HUMID", codes)
        self.assertFalse(res.irrigation_status.needs_water)
        self.assertIn("fungal", res.overall_summary.lower())

    def test_compound_high_heat_and_high_humidity(self):
        # Temperature 37°C (>35°C) and Humidity 78% (>70%)
        reading = SensorReading(soil_moisture=45.0, temperature=37.0, humidity=78.0)
        res = evaluate_farm_intelligence(reading)
        codes = [c.code for c in res.conditions]
        self.assertIn("COMPOUND_HEAT_HUMID", codes)


class TestFarmContextInfluence(unittest.TestCase):
    """Verify context modulation without compromising safety."""

    def test_crop_mention_in_summary(self):
        reading = SensorReading(soil_moisture=22.0, temperature=28.0, humidity=50.0)
        res = evaluate_farm_intelligence(reading, farm_context={"crop": "Tomato"})
        self.assertIn("Tomato", res.overall_summary)

    def test_flowering_stage_escalates_severity(self):
        # Moisture 18% (<20%) without stage -> alert; with Flowering -> critical
        reading = SensorReading(soil_moisture=18.0, temperature=28.0, humidity=50.0)
        res_standard = evaluate_farm_intelligence(reading)
        self.assertEqual(res_standard.conditions[0].severity, "alert")

        res_flowering = evaluate_farm_intelligence(
            reading, farm_context={"crop": "Tomato", "growth_stage": "Flowering"}
        )
        self.assertEqual(res_flowering.conditions[0].severity, "critical")
        self.assertIn("Flowering", res_flowering.conditions[0].explanation)

    def test_sandy_soil_note(self):
        reading = SensorReading(soil_moisture=18.0, temperature=28.0, humidity=50.0)
        res_sand = evaluate_farm_intelligence(
            reading, farm_context={"crop": "Groundnut", "soil_type": "Sandy Soil"}
        )
        self.assertIn("Sandy Soil", res_sand.conditions[0].explanation)

    def test_clay_soil_waterlogging_escalation(self):
        reading = SensorReading(soil_moisture=78.0, temperature=25.0, humidity=60.0)
        res_clay = evaluate_farm_intelligence(
            reading, farm_context={"crop": "Rice", "soil_type": "Clay Soil"}
        )
        # Saturated clay escalates to alert
        self.assertEqual(res_clay.conditions[0].severity, "alert")

    def test_missing_farm_context_graceful_handling(self):
        # Empty context must not raise and must not invent fields
        reading = SensorReading(soil_moisture=45.0, temperature=26.0, humidity=60.0)
        res = evaluate_farm_intelligence(reading, farm_context={})
        self.assertEqual(res.primary_status, "Optimal Conditions")
        self.assertNotIn("None", res.overall_summary)
        self.assertNotIn("undefined", res.overall_summary)


class TestSeverityOrdering(unittest.TestCase):
    """Verify conditions are strictly ordered by severity priority."""

    def test_conditions_sorted_by_severity(self):
        # Dry soil (alert/critical) + High Temp (warning) + High Humidity (warning)
        reading = SensorReading(soil_moisture=15.0, temperature=38.0, humidity=85.0)
        res = evaluate_farm_intelligence(reading)

        severities = [c.severity for c in res.conditions]
        weight_map = {"critical": 50, "alert": 40, "warning": 30, "good": 20, "info": 10}
        numeric_weights = [weight_map[s] for s in severities]

        # Must be descending
        self.assertEqual(numeric_weights, sorted(numeric_weights, reverse=True))


if __name__ == "__main__":
    unittest.main()
