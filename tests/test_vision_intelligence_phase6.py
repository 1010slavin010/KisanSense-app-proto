"""Comprehensive Phase 6 integration and verification test suite.

Verifies:
1. Image Formats: PNG, JPEG, WEBP
2. Input edge cases: Invalid bytes, empty payload, 10MB payload size limit
3. Image Quality Gate: Low resolution, underexposed, overexposed, blurry, non-plant
4. Diagnoses: Healthy foliage, Tomato Early Blight, Potato Late Blight, Chlorosis, Generic Foliar
5. Extended fields: symptoms_detected, affected_foliage_ratio, treatment_urgency
6. Confidence calibration and tiers (high, moderate, low)
7. Deterministic reproducibility
8. Farm context: Crop specified vs missing crop fallback
9. Farm Intelligence integration:
   - High humidity + fungal/blight compound risk
   - Low moisture + chlorosis compound risk
   - High moisture + chlorosis compound risk
   - Sensor offline safety: needs_water remains False, vision is advisory only
   - Sensor fault safety: needs_water remains False
   - Sensor stale safety: needs_water remains False
   - Vision NEVER directly turns on irrigation
10. Chatbot Grounding:
   - "Is my plant healthy?"
   - "What disease might this be?"
   - "Why is my plant unhealthy?"
   - "What should I do?"
   - Graceful fallback when vision_result is absent (no hallucinations)
11. Translation completeness across en, hi, ta, kn for all Phase 6 keys
"""

from __future__ import annotations

import io
import unittest
import numpy as np
from PIL import Image

from services.ai_service import get_ai_response
from services.farm_intelligence import evaluate_farm_intelligence
from services.sensor_service import SensorReading
from services.vision_service import (
    VisionAnalysisResult,
    analyze_plant_image,
)
from utils.translations import TRANSLATIONS


def _generate_synthetic_image(
    format_type: str = "PNG",
    size: tuple[int, int] = (256, 256),
    color: tuple[int, int, int] = (40, 160, 40),
) -> bytes:
    """Create a valid in-memory image in PNG, JPEG, or WEBP format."""
    arr = np.zeros((size[1], size[0], 3), dtype=np.uint8)
    arr[:, :] = color
    # Add texture variance so it passes the sharpness check even under lossy compression
    arr[::2, ::2, 1] = min(255, color[1] + 30)
    arr[1::2, 1::2, 0] = max(0, color[0] - 20)
    img = Image.fromarray(arr)

    buf = io.BytesIO()
    if format_type.upper() == "WEBP":
        img.save(buf, format="WEBP", lossless=True)
    else:
        img.save(buf, format=format_type)
    return buf.getvalue()


class TestVisionFormatsAndPayloads(unittest.TestCase):
    """Test image format support and payload safety limits."""

    def test_png_format_supported(self):
        png_data = _generate_synthetic_image("PNG")
        result = analyze_plant_image(png_data, farm_context={"crop": "Tomato"})
        self.assertTrue(result.success)
        self.assertEqual(result.disease_code, "HEALTHY_FOLIAGE")

    def test_jpeg_format_supported(self):
        jpeg_data = _generate_synthetic_image("JPEG")
        result = analyze_plant_image(jpeg_data, farm_context={"crop": "Tomato"})
        self.assertTrue(result.success)
        self.assertEqual(result.disease_code, "HEALTHY_FOLIAGE")

    def test_webp_format_supported(self):
        webp_data = _generate_synthetic_image("WEBP")
        result = analyze_plant_image(webp_data, farm_context={"crop": "Tomato"})
        self.assertTrue(result.success)
        self.assertEqual(result.disease_code, "HEALTHY_FOLIAGE")

    def test_empty_image_input(self):
        result = analyze_plant_image(None)
        self.assertFalse(result.success)
        self.assertEqual(result.disease_code, "NO_IMAGE")
        self.assertEqual(result.confidence_level, "low")

    def test_invalid_image_bytes(self):
        result = analyze_plant_image(b"invalid_non_image_bytes_here")
        self.assertFalse(result.success)
        self.assertEqual(result.disease_code, "CORRUPTED_FILE")

    def test_payload_exceeding_10mb_rejected(self):
        fake_huge_payload = b"0" * (10 * 1024 * 1024 + 1)
        result = analyze_plant_image(fake_huge_payload)
        self.assertFalse(result.success)
        self.assertEqual(result.disease_code, "PAYLOAD_TOO_LARGE")
        self.assertIn("10MB", result.explanation)


class TestVisionQualityGate(unittest.TestCase):
    """Test all quality rejection conditions before disease screening."""

    def test_low_resolution_rejected(self):
        small = _generate_synthetic_image("PNG", size=(64, 64))
        result = analyze_plant_image(small)
        self.assertFalse(result.success)
        self.assertEqual(result.image_quality, "low_resolution")

    def test_underexposure_rejected(self):
        dark = _generate_synthetic_image("PNG", color=(10, 20, 10))
        result = analyze_plant_image(dark)
        self.assertFalse(result.success)
        self.assertEqual(result.image_quality, "underexposed")

    def test_overexposure_rejected(self):
        bright = _generate_synthetic_image("PNG", color=(250, 250, 245))
        result = analyze_plant_image(bright)
        self.assertFalse(result.success)
        self.assertEqual(result.image_quality, "overexposed")

    def test_non_plant_rejected(self):
        blue = _generate_synthetic_image("PNG", color=(20, 40, 200))
        result = analyze_plant_image(blue)
        self.assertFalse(result.success)
        self.assertEqual(result.image_quality, "non_plant")

    def test_blur_rejected(self):
        # Uniform solid flat image with zero variance across gradients
        flat_arr = np.full((200, 200, 3), [40, 160, 40], dtype=np.uint8)
        img = Image.fromarray(flat_arr)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        result = analyze_plant_image(buf.getvalue())
        self.assertFalse(result.success)
        self.assertEqual(result.image_quality, "blurry")


class TestVisionDiagnosisAndExtendedFields(unittest.TestCase):
    """Test foliar disease classifications and backward-compatible fields."""

    def test_healthy_foliage_extended_fields(self):
        data = _generate_synthetic_image("PNG", color=(40, 160, 40))
        result = analyze_plant_image(data, farm_context={"crop": "Tomato"})
        self.assertTrue(result.success)
        self.assertTrue(result.healthy)
        self.assertEqual(result.symptoms_detected, [])
        self.assertEqual(result.affected_foliage_ratio, 0.0)
        self.assertEqual(result.treatment_urgency, "none")
        self.assertGreaterEqual(result.confidence, 0.80)
        self.assertEqual(result.confidence_level, "high")

    def test_early_blight_symptoms_and_urgency(self):
        arr = np.zeros((256, 256, 3), dtype=np.uint8)
        arr[:, :] = [45, 160, 45]
        arr[40:80, 40:80] = [120, 75, 25]  # Necrotic spot
        arr[120:160, 120:160] = [115, 70, 20]

        img = Image.fromarray(arr)
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        result = analyze_plant_image(buf.getvalue(), farm_context={"crop": "Tomato"})
        self.assertTrue(result.success)
        self.assertFalse(result.healthy)
        self.assertEqual(result.disease_code, "TOMATO_EARLY_BLIGHT")
        self.assertEqual(result.treatment_urgency, "moderate")
        self.assertIn("concentric_target_spots", result.symptoms_detected)
        self.assertGreater(result.affected_foliage_ratio, 0.0)

    def test_late_blight_dark_rot_urgency(self):
        arr = np.zeros((256, 256, 3), dtype=np.uint8)
        arr[:, :] = [40, 150, 40]
        arr[30:100, 30:100] = [50, 35, 20]  # Dark rot
        arr[140:190, 140:190] = [45, 30, 15]

        img = Image.fromarray(arr)
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        result = analyze_plant_image(buf.getvalue(), farm_context={"crop": "Potato"})
        self.assertTrue(result.success)
        self.assertFalse(result.healthy)
        self.assertEqual(result.disease_code, "POTATO_LATE_BLIGHT")
        self.assertEqual(result.treatment_urgency, "immediate")
        self.assertIn("dark_water_soaked_spots", result.symptoms_detected)

    def test_chlorosis_nutrient_stress(self):
        arr = np.zeros((256, 256, 3), dtype=np.uint8)
        arr[:, :] = [45, 155, 45]
        arr[30:200, 30:200] = [190, 180, 40]  # Yellowing

        img = Image.fromarray(arr)
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        result = analyze_plant_image(buf.getvalue(), farm_context={"crop": "Tomato"})
        self.assertTrue(result.success)
        self.assertFalse(result.healthy)
        self.assertEqual(result.disease_code, "NUTRIENT_CHLOROSIS")
        self.assertEqual(result.category, "abiotic_stress")
        self.assertEqual(result.treatment_urgency, "routine")
        self.assertIn("leaf_yellowing", result.symptoms_detected)

    def test_rice_leaf_blast_context(self):
        arr = np.zeros((256, 256, 3), dtype=np.uint8)
        arr[:, :] = [45, 160, 45]
        arr[40:80, 40:80] = [120, 75, 25]

        img = Image.fromarray(arr)
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        result = analyze_plant_image(buf.getvalue(), farm_context={"crop": "Rice"})
        self.assertEqual(result.disease_code, "RICE_LEAF_BLAST")
        self.assertIn("Rice", result.diagnosis)

    def test_cotton_blight_context(self):
        arr = np.zeros((256, 256, 3), dtype=np.uint8)
        arr[:, :] = [45, 160, 45]
        arr[40:80, 40:80] = [120, 75, 25]

        img = Image.fromarray(arr)
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        result = analyze_plant_image(buf.getvalue(), farm_context={"crop": "Cotton"})
        self.assertEqual(result.disease_code, "COTTON_BLIGHT")
        self.assertIn("Cotton", result.diagnosis)

    def test_missing_crop_context_fallback(self):
        arr = np.zeros((256, 256, 3), dtype=np.uint8)
        arr[:, :] = [45, 160, 45]
        arr[40:80, 40:80] = [120, 75, 25]

        img = Image.fromarray(arr)
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        result = analyze_plant_image(buf.getvalue(), farm_context={})
        self.assertEqual(result.disease_code, "FOLIAR_LEAF_SPOT")
        self.assertEqual(result.crop, "Crop")

    def test_deterministic_repeatability(self):
        data = _generate_synthetic_image("PNG")
        res_a = analyze_plant_image(data, farm_context={"crop": "Tomato"})
        res_b = analyze_plant_image(data, farm_context={"crop": "Tomato"})
        self.assertEqual(res_a.disease_code, res_b.disease_code)
        self.assertEqual(res_a.confidence, res_b.confidence)
        self.assertEqual(res_a.diagnosis, res_b.diagnosis)
        self.assertEqual(res_a.symptoms_detected, res_b.symptoms_detected)


class TestVisionFarmIntelligenceIntegration(unittest.TestCase):
    """Test synthesis with Smart Farm Intelligence and strict safety preservation."""

    def setUp(self):
        self.healthy_vision = VisionAnalysisResult(
            success=True,
            is_plant=True,
            healthy=True,
            diagnosis="Healthy Tomato Foliage",
            disease_code="HEALTHY_FOLIAGE",
            crop="Tomato",
            category="healthy",
            confidence=0.88,
            confidence_level="high",
            explanation="Foliage appears vibrant and uniform.",
            recommended_action="Continue routine monitoring.",
            image_quality="good",
            symptoms_detected=[],
            affected_foliage_ratio=0.0,
            treatment_urgency="none",
        )
        self.blight_vision = VisionAnalysisResult(
            success=True,
            is_plant=True,
            healthy=False,
            diagnosis="Early Blight Suspected",
            disease_code="TOMATO_EARLY_BLIGHT",
            crop="Tomato",
            category="fungal",
            confidence=0.84,
            confidence_level="high",
            explanation="Target-like necrotic lesions detected on foliage.",
            recommended_action="Prune visibly affected lower foliage.",
            image_quality="good",
            symptoms_detected=["concentric_target_spots"],
            affected_foliage_ratio=0.08,
            treatment_urgency="moderate",
        )
        self.chlorosis_vision = VisionAnalysisResult(
            success=True,
            is_plant=True,
            healthy=False,
            diagnosis="Foliar Yellowing / Chlorosis",
            disease_code="NUTRIENT_CHLOROSIS",
            crop="Tomato",
            category="abiotic_stress",
            confidence=0.76,
            confidence_level="moderate",
            explanation="Foliar yellowing observed across leaf tissue.",
            recommended_action="Verify root-zone soil moisture and drainage.",
            image_quality="good",
            symptoms_detected=["leaf_yellowing"],
            affected_foliage_ratio=0.22,
            treatment_urgency="routine",
        )

    def test_high_humidity_and_fungal_compound_risk(self):
        reading = SensorReading(
            soil_moisture=50.0,
            temperature=26.0,
            humidity=82.0,  # High humidity > 75%
            is_online=True,
        )
        intel = evaluate_farm_intelligence(
            reading,
            farm_context={"crop": "Tomato"},
            vision_result=self.blight_vision,
        )
        codes = [c.code for c in intel.conditions]
        self.assertIn("COMPOUND_FUNGAL_HUMIDITY", codes)
        comp_cond = next(c for c in intel.conditions if c.code == "COMPOUND_FUNGAL_HUMIDITY")
        self.assertIn("overhead watering", comp_cond.recommended_action.lower())

    def test_dry_soil_and_chlorosis_compound_risk(self):
        reading = SensorReading(
            soil_moisture=22.0,  # Low soil moisture < 30%
            temperature=28.0,
            humidity=50.0,
            is_online=True,
        )
        intel = evaluate_farm_intelligence(
            reading,
            farm_context={"crop": "Tomato"},
            vision_result=self.chlorosis_vision,
        )
        codes = [c.code for c in intel.conditions]
        self.assertIn("COMPOUND_DRY_CHLOROSIS", codes)
        comp_cond = next(c for c in intel.conditions if c.code == "COMPOUND_DRY_CHLOROSIS")
        self.assertIn("root-zone moisture", comp_cond.recommended_action.lower())

    def test_saturated_soil_and_chlorosis_compound_risk(self):
        reading = SensorReading(
            soil_moisture=78.0,  # High soil moisture > 70%
            temperature=24.0,
            humidity=60.0,
            is_online=True,
        )
        intel = evaluate_farm_intelligence(
            reading,
            farm_context={"crop": "Tomato"},
            vision_result=self.chlorosis_vision,
        )
        codes = [c.code for c in intel.conditions]
        self.assertIn("COMPOUND_WET_CHLOROSIS", codes)
        comp_cond = next(c for c in intel.conditions if c.code == "COMPOUND_WET_CHLOROSIS")
        self.assertIn("do not add irrigation", comp_cond.recommended_action.lower())

    def test_sensor_offline_safety_preserved_with_vision(self):
        reading = SensorReading(
            soil_moisture=0.0,
            temperature=0.0,
            humidity=0.0,
            is_online=False,  # Sensor Offline
        )
        intel = evaluate_farm_intelligence(
            reading,
            farm_context={"crop": "Tomato"},
            vision_result=self.blight_vision,
        )
        self.assertEqual(intel.data_quality, "offline")
        self.assertFalse(intel.irrigation_status.needs_water)
        # Vision must be appended strictly as an advisory condition
        foliar_conds = [c for c in intel.conditions if c.category == "foliar_health"]
        self.assertEqual(len(foliar_conds), 1)
        self.assertIn("Advisory", foliar_conds[0].title)

    def test_sensor_fault_safety_preserved_with_vision(self):
        reading = SensorReading(
            soil_moisture=45.0,
            temperature=25.0,
            humidity=50.0,
            is_online=True,
            raw_status="hardware_fault",
        )
        intel = evaluate_farm_intelligence(
            reading,
            farm_context={"crop": "Tomato"},
            vision_result=self.blight_vision,
        )
        self.assertEqual(intel.data_quality, "fault")
        self.assertFalse(intel.irrigation_status.needs_water)

    def test_sensor_stale_safety_preserved_with_vision(self):
        reading = SensorReading(
            soil_moisture=45.0,
            temperature=25.0,
            humidity=50.0,
            is_online=True,
            raw_status="stale_or_offline",
        )
        intel = evaluate_farm_intelligence(
            reading,
            farm_context={"crop": "Tomato"},
            vision_result=self.blight_vision,
        )
        self.assertEqual(intel.data_quality, "stale")
        self.assertFalse(intel.irrigation_status.needs_water)

    def test_vision_never_directly_triggers_irrigation(self):
        # Soil moisture is 55% (adequate, no water needed). Blight is detected.
        reading = SensorReading(
            soil_moisture=55.0,
            temperature=25.0,
            humidity=60.0,
            is_online=True,
        )
        intel = evaluate_farm_intelligence(
            reading,
            farm_context={"crop": "Tomato"},
            vision_result=self.blight_vision,
        )
        # Irrigation status must remain False!
        self.assertFalse(intel.irrigation_status.needs_water)


class TestChatbotVisionGrounding(unittest.TestCase):
    """Test Chatbot responses with and without structured vision_result context."""

    def setUp(self):
        self.healthy_vision = VisionAnalysisResult(
            success=True,
            is_plant=True,
            healthy=True,
            diagnosis="Healthy Tomato Foliage",
            disease_code="HEALTHY_FOLIAGE",
            crop="Tomato",
            category="healthy",
            confidence=0.90,
            confidence_level="high",
            explanation="Tomato foliage appears vibrant and uniform.",
            recommended_action="Continue routine monitoring.",
            image_quality="good",
        )
        self.blight_vision = VisionAnalysisResult(
            success=True,
            is_plant=True,
            healthy=False,
            diagnosis="Early Blight Suspected",
            disease_code="TOMATO_EARLY_BLIGHT",
            crop="Tomato",
            category="fungal",
            confidence=0.82,
            confidence_level="high",
            explanation="Target-like necrotic lesions detected on leaf.",
            recommended_action="Prune visibly affected lower foliage.",
            image_quality="good",
            symptoms_detected=["concentric_target_spots"],
            affected_foliage_ratio=0.08,
            treatment_urgency="moderate",
        )

    def test_is_my_plant_healthy_with_healthy_vision(self):
        reply = get_ai_response(
            "Is my plant healthy?",
            context={"crop": "Tomato", "vision_result": self.healthy_vision},
        )
        self.assertIn("healthy", reply.lower())
        self.assertIn("90%", reply)
        self.assertIn("routine monitoring", reply.lower())

    def test_is_my_plant_healthy_with_blight_vision(self):
        reply = get_ai_response(
            "Is my plant healthy?",
            context={"crop": "Tomato", "vision_result": self.blight_vision},
        )
        self.assertIn("early blight", reply.lower())
        self.assertIn("82%", reply)
        self.assertIn("prune", reply.lower())

    def test_is_my_plant_healthy_without_vision(self):
        reply = get_ai_response(
            "Is my plant healthy?",
            context={"crop": "Tomato", "vision_result": None},
        )
        self.assertIn("no plant leaf has been scanned yet", reply.lower())
        self.assertNotIn("early blight", reply.lower())

    def test_what_disease_might_this_be_with_blight(self):
        reply = get_ai_response(
            "What disease might this be?",
            context={"crop": "Tomato", "vision_result": self.blight_vision},
        )
        self.assertIn("early blight", reply.lower())
        self.assertIn("TOMATO_EARLY_BLIGHT", reply)
        self.assertIn("high", reply.lower())

    def test_what_disease_without_vision(self):
        reply = get_ai_response(
            "What disease might this be?",
            context={"crop": "Tomato", "vision_result": None},
        )
        self.assertIn("no plant leaf scan is currently available", reply.lower())

    def test_why_is_my_plant_unhealthy_with_blight(self):
        reply = get_ai_response(
            "Why is my plant unhealthy?",
            context={"crop": "Tomato", "vision_result": self.blight_vision},
        )
        self.assertIn("necrotic lesions", reply.lower())
        self.assertIn("concentric_target_spots", reply)

    def test_what_should_i_do_with_blight(self):
        reply = get_ai_response(
            "What should I do about this disease?",
            context={"crop": "Tomato", "vision_result": self.blight_vision},
        )
        self.assertIn("prune", reply.lower())


class TestPhase6Translations(unittest.TestCase):
    """Test translation dictionary coverage across English, Hindi, Tamil, and Kannada."""

    def test_required_phase6_translation_keys_exist(self):
        required_keys = [
            "home_plant_health_title",
            "home_plant_health_no_scan",
            "home_plant_health_scan_now",
            "home_plant_health_view_scan",
            "home_plant_health_status_healthy",
            "home_plant_health_status_issue",
            "home_plant_health_urgency",
            "vision_tab_upload",
            "vision_tab_camera",
            "vision_camera_help",
            "vision_symptoms_detected",
            "vision_affected_area",
            "vision_urgency_title",
            "vision_urgency_immediate",
            "vision_urgency_moderate",
            "vision_urgency_routine",
            "vision_urgency_none",
        ]
        for lang in ("en", "hi", "ta", "kn"):
            self.assertIn(lang, TRANSLATIONS)
            lang_dict = TRANSLATIONS[lang]
            for key in required_keys:
                self.assertIn(
                    key,
                    lang_dict,
                    f"Missing translation key '{key}' in language '{lang}'",
                )
                self.assertTrue(
                    len(lang_dict[key].strip()) > 0,
                    f"Empty translation string for key '{key}' in '{lang}'",
                )


if __name__ == "__main__":
    unittest.main()
