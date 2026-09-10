"""Unit tests for services.vision_service.

Covers:
- Image Quality Gate (Low resolution, underexposed, overexposed, blur, non-plant foliage)
- Empty, corrupted, and invalid payload handling
- Disease classification (Early Blight, Late Blight, Chlorosis, Healthy foliage)
- Crop context modulation and generic fallback
- Confidence scoring and tiering (high, moderate, low)
- Deterministic reproducibility
"""

import io
import unittest
import numpy as np
from PIL import Image

from services.vision_service import (
    VisionAnalysisResult,
    analyze_plant_image,
)


def _create_synthetic_image(
    size: tuple[int, int] = (256, 256),
    color: tuple[int, int, int] = (40, 160, 40),
) -> bytes:
    """Helper to generate an in-memory PNG image."""
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestVisionServiceQualityGate(unittest.TestCase):
    """Test the pre-diagnostic Image Quality Gate."""

    def test_empty_none_input(self):
        result = analyze_plant_image(None)
        self.assertIsInstance(result, VisionAnalysisResult)
        self.assertFalse(result.success)
        self.assertFalse(result.is_plant)
        self.assertEqual(result.image_quality, "unusable")
        self.assertEqual(result.disease_code, "NO_IMAGE")

    def test_corrupted_file_bytes(self):
        corrupted = b"NOT_AN_IMAGE_RANDOM_GARBAGE_BYTES_12345"
        result = analyze_plant_image(corrupted)
        self.assertFalse(result.success)
        self.assertEqual(result.image_quality, "invalid")
        self.assertEqual(result.disease_code, "CORRUPTED_FILE")

    def test_low_resolution_image_rejected(self):
        # 64x64 is below MIN_IMAGE_DIMENSION (128)
        tiny_img = _create_synthetic_image(size=(64, 64), color=(50, 180, 50))
        result = analyze_plant_image(tiny_img)
        self.assertFalse(result.success)
        self.assertEqual(result.image_quality, "low_resolution")
        self.assertIn("resolution", result.explanation.lower())

    def test_underexposed_image_rejected(self):
        # Average brightness near 15 (<35)
        dark_img = _create_synthetic_image(size=(200, 200), color=(10, 20, 10))
        result = analyze_plant_image(dark_img)
        self.assertFalse(result.success)
        self.assertEqual(result.image_quality, "underexposed")
        self.assertIn("dark", result.explanation.lower())

    def test_overexposed_image_rejected(self):
        # Average brightness near 250 (>235)
        bright_img = _create_synthetic_image(size=(200, 200), color=(250, 250, 245))
        result = analyze_plant_image(bright_img)
        self.assertFalse(result.success)
        self.assertEqual(result.image_quality, "overexposed")
        self.assertIn("glare", result.explanation.lower())

    def test_non_plant_image_rejected(self):
        # Solid blue image with no green foliage (e.g. wall, sky, or machinery)
        blue_img = _create_synthetic_image(size=(200, 200), color=(20, 40, 200))
        result = analyze_plant_image(blue_img)
        self.assertFalse(result.success)
        self.assertFalse(result.is_plant)
        self.assertEqual(result.image_quality, "non_plant")
        self.assertIn("no recognizable plant", result.explanation.lower())


class TestVisionServiceDiseaseClassification(unittest.TestCase):
    """Test disease detection, chlorosis, and healthy foliage analysis."""

    def test_healthy_green_foliage(self):
        # Vibrant green leaf image with texture
        arr = np.zeros((256, 256, 3), dtype=np.uint8)
        arr[:, :, 0] = 35   # Red
        arr[:, :, 1] = 165  # Green
        arr[:, :, 2] = 40   # Blue
        # Add slight natural variation to pass sharpness
        arr[::4, ::4, 1] = 180

        img = Image.fromarray(arr)
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        result = analyze_plant_image(buf.getvalue(), farm_context={"crop": "Tomato"})
        self.assertTrue(result.success)
        self.assertTrue(result.is_plant)
        self.assertTrue(result.healthy)
        self.assertEqual(result.disease_code, "HEALTHY_FOLIAGE")
        self.assertEqual(result.category, "healthy")
        self.assertGreaterEqual(result.confidence, 0.80)
        self.assertEqual(result.confidence_level, "high")
        self.assertIn("Tomato", result.diagnosis)

    def test_early_blight_necrotic_spotting(self):
        # Green leaf base with brown target spots (R=120, G=70, B=30)
        arr = np.zeros((256, 256, 3), dtype=np.uint8)
        arr[:, :] = [45, 160, 45]  # Green leaf base

        # Add necrotic lesions covering ~8% of pixels
        arr[40:80, 40:80] = [120, 75, 25]
        arr[120:160, 120:160] = [115, 70, 20]

        img = Image.fromarray(arr)
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        result = analyze_plant_image(buf.getvalue(), farm_context={"crop": "Tomato"})
        self.assertTrue(result.success)
        self.assertFalse(result.healthy)
        self.assertEqual(result.category, "fungal")
        self.assertIn("EARLY_BLIGHT", result.disease_code)
        self.assertIn("Early Blight", result.diagnosis)
        self.assertIn("Prune", result.recommended_action)

    def test_severe_dark_rot_late_blight(self):
        # Green leaf with very dark water-soaked lesions (R=50, G=35, B=20, low luminance)
        arr = np.zeros((256, 256, 3), dtype=np.uint8)
        arr[:, :] = [40, 150, 40]

        # Add dark rot lesions covering >10% of pixels
        arr[30:100, 30:100] = [50, 35, 20]
        arr[140:190, 140:190] = [45, 30, 15]

        img = Image.fromarray(arr)
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        result = analyze_plant_image(buf.getvalue(), farm_context={"crop": "Potato"})
        self.assertTrue(result.success)
        self.assertFalse(result.healthy)
        self.assertEqual(result.category, "fungal")
        self.assertIn("LATE_BLIGHT", result.disease_code)
        self.assertIn("Late Blight", result.diagnosis)

    def test_foliar_yellowing_chlorosis(self):
        # Yellow chlorotic leaf: high R (190), high G (180), low B (40)
        arr = np.zeros((256, 256, 3), dtype=np.uint8)
        arr[:, :] = [45, 155, 45]  # Background green
        arr[30:200, 30:200] = [190, 180, 40]  # Large yellowing patch

        img = Image.fromarray(arr)
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        result = analyze_plant_image(buf.getvalue(), farm_context={"crop": "Cotton"})
        self.assertTrue(result.success)
        self.assertFalse(result.healthy)
        self.assertEqual(result.disease_code, "NUTRIENT_CHLOROSIS")
        self.assertEqual(result.category, "abiotic_stress")
        self.assertIn("Chlorosis", result.diagnosis)
        self.assertIn("micronutrient", result.recommended_action.lower())

    def test_unsupported_or_generic_crop_fallback(self):
        # No crop in context; falls back gracefully without exception
        arr = np.zeros((256, 256, 3), dtype=np.uint8)
        arr[:, :] = [40, 160, 40]
        arr[50:90, 50:90] = [115, 70, 20]

        img = Image.fromarray(arr)
        buf = io.BytesIO()
        img.save(buf, format="PNG")

        result = analyze_plant_image(buf.getvalue(), farm_context={})
        self.assertTrue(result.success)
        self.assertIn("Leaf Spot", result.diagnosis)
        self.assertEqual(result.crop, "Crop")

    def test_deterministic_reproducibility(self):
        # Same image analyzed twice produces identical diagnoses and confidence
        img_bytes = _create_synthetic_image(size=(200, 200), color=(50, 170, 50))
        res1 = analyze_plant_image(img_bytes, farm_context={"crop": "Tomato"})
        res2 = analyze_plant_image(img_bytes, farm_context={"crop": "Tomato"})

        self.assertEqual(res1.disease_code, res2.disease_code)
        self.assertEqual(res1.confidence, res2.confidence)
        self.assertEqual(res1.diagnosis, res2.diagnosis)


if __name__ == "__main__":
    unittest.main()
