"""Unit tests for FarmProfile model, validation, and context extraction."""

import unittest
from services.farm_service import (
    FarmProfile,
    get_farm_context,
    is_profile_configured,
    validate_farm_profile,
)


class TestFarmProfile(unittest.TestCase):
    def test_default_farm_profile(self):
        p = FarmProfile()
        self.assertEqual(p.crop, "")
        self.assertEqual(p.farm_name, "")
        self.assertIsNone(p.farm_area)
        self.assertFalse(is_profile_configured(p))

    def test_to_dict_and_from_dict(self):
        p = FarmProfile(
            farm_name="Sunset Orchard",
            farmer_name="Anita",
            location="Pune, MH",
            crop="Tomato",
            crop_variety="Arka Rakshak",
            growth_stage="Flowering",
            soil_type="Loamy Soil",
            farm_area=4.5,
            area_unit="Acres",
            irrigation_method="Drip Irrigation",
        )
        d = p.to_dict()
        self.assertEqual(d["crop"], "Tomato")
        self.assertEqual(d["farm_area"], 4.5)

        restored = FarmProfile.from_dict(d)
        self.assertEqual(restored.crop, "Tomato")
        self.assertEqual(restored.farmer_name, "Anita")
        self.assertEqual(restored.farm_area, 4.5)
        self.assertTrue(is_profile_configured(restored))

    def test_validate_farm_profile_required_crop(self):
        # Empty crop is invalid
        valid, errors = validate_farm_profile({"crop": "", "farm_area": 5.0})
        self.assertFalse(valid)
        self.assertIn("crop", errors)

        # Whitespace crop is invalid
        valid, errors = validate_farm_profile({"crop": "   ", "farm_area": 5.0})
        self.assertFalse(valid)
        self.assertIn("crop", errors)

        # Valid crop
        valid, errors = validate_farm_profile({"crop": "Wheat", "farm_area": 2.0})
        self.assertTrue(valid)
        self.assertEqual(len(errors), 0)

    def test_validate_farm_profile_area(self):
        # Negative area is invalid
        valid, errors = validate_farm_profile({"crop": "Rice", "farm_area": -1.5})
        self.assertFalse(valid)
        self.assertIn("farm_area", errors)

        # Non-numeric area is invalid
        valid, errors = validate_farm_profile({"crop": "Rice", "farm_area": "abc"})
        self.assertFalse(valid)
        self.assertIn("farm_area", errors)

        # Zero or positive area is valid
        valid, errors = validate_farm_profile({"crop": "Rice", "farm_area": 0.0})
        self.assertTrue(valid)

        valid, errors = validate_farm_profile({"crop": "Rice", "farm_area": 12.5})
        self.assertTrue(valid)

        # None area is valid (area is optional)
        valid, errors = validate_farm_profile({"crop": "Rice", "farm_area": None})
        self.assertTrue(valid)


if __name__ == "__main__":
    unittest.main()
