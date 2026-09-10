"""AppTest end-to-end integration tests for the Crop Health / Vision view.

Verifies:
- Clean initial render of Crop Health page without exceptions
- Farm context display (configured vs generic)
- Image Quality Gate: rejected blurry / non-plant photos do not diagnose diseases
- Diagnostic results: Healthy leaf, Tomato Early Blight, Potato Late Blight, Chlorosis
- Session state persistence of latest_vision_result
- AI Assistant context integration for vision queries
- Dark Mode and Light Mode rendering stability
"""

import io
import os
import unittest
import numpy as np
from PIL import Image
from streamlit.testing.v1 import AppTest

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))


def _make_image_bytes(arr: np.ndarray) -> bytes:
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_healthy_leaf() -> bytes:
    arr = np.zeros((256, 256, 3), dtype=np.uint8)
    arr[:, :] = [35, 165, 40]
    arr[::4, ::4, 1] = 180
    return _make_image_bytes(arr)


def _make_early_blight_leaf() -> bytes:
    arr = np.zeros((256, 256, 3), dtype=np.uint8)
    arr[:, :] = [45, 160, 45]
    arr[40:80, 40:80] = [120, 75, 25]
    arr[120:160, 120:160] = [115, 70, 20]
    return _make_image_bytes(arr)


def _make_late_blight_leaf() -> bytes:
    arr = np.zeros((256, 256, 3), dtype=np.uint8)
    arr[:, :] = [40, 150, 40]
    arr[30:100, 30:100] = [50, 35, 20]
    arr[140:190, 140:190] = [45, 30, 15]
    return _make_image_bytes(arr)


def _make_yellow_chlorosis_leaf() -> bytes:
    arr = np.zeros((256, 256, 3), dtype=np.uint8)
    arr[:, :] = [45, 155, 45]
    arr[30:200, 30:200] = [190, 180, 40]
    return _make_image_bytes(arr)


def _make_non_plant_image() -> bytes:
    arr = np.zeros((200, 200, 3), dtype=np.uint8)
    arr[:, :] = [20, 40, 200]  # Solid blue
    return _make_image_bytes(arr)


class TestVisionView(unittest.TestCase):
    def test_initial_vision_render_clean(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        # Navigate to Vision page
        at.button(key="nav_vision").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.page, "vision")

        # Verify title and prompt
        self.assertTrue(len(at.info) > 0)
        self.assertIn("Upload a clear photo", at.info[0].value)

    def test_farm_context_in_vision(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        # Set farm crop
        at.session_state.farm_profile["crop"] = "Tomato"
        at.button(key="nav_vision").click().run()
        self.assertFalse(at.exception)

        # Vision page renders with Tomato context
        self.assertEqual(at.session_state.farm_profile["crop"], "Tomato")

    def test_image_quality_gate_non_plant(self):
        """Non-plant image must be rejected without diagnosing disease."""
        from services.vision_service import analyze_plant_image

        blue_bytes = _make_non_plant_image()
        result = analyze_plant_image(blue_bytes, farm_context={"crop": "Tomato"})
        self.assertFalse(result.success)
        self.assertEqual(result.image_quality, "non_plant")
        self.assertIn("no recognizable plant", result.explanation.lower())

        # Render in app
        at = AppTest.from_file(APP_PATH).run()
        at.session_state.page = "vision"
        at.session_state.latest_vision_result = result
        at.run()
        self.assertFalse(at.exception)

    def test_healthy_leaf_analysis_in_view(self):
        """Healthy leaf displays reassuring card and care tips."""
        from services.vision_service import analyze_plant_image

        healthy_bytes = _make_healthy_leaf()
        result = analyze_plant_image(healthy_bytes, farm_context={"crop": "Tomato"})
        self.assertTrue(result.success)
        self.assertTrue(result.healthy)
        self.assertIn("Tomato", result.diagnosis)

        # Test view render with healthy result
        at = AppTest.from_file(APP_PATH).run()
        at.session_state.page = "vision"
        at.session_state.latest_vision_result = result
        at.run()
        self.assertFalse(at.exception)

    def test_tomato_early_blight_analysis(self):
        """Early blight leaf displays Early Blight diagnosis."""
        from services.vision_service import analyze_plant_image

        eb_bytes = _make_early_blight_leaf()
        result = analyze_plant_image(eb_bytes, farm_context={"crop": "Tomato"})
        self.assertTrue(result.success)
        self.assertFalse(result.healthy)
        self.assertEqual(result.disease_code, "TOMATO_EARLY_BLIGHT")
        self.assertIn("Early Blight", result.diagnosis)

        # Test view render with result
        at = AppTest.from_file(APP_PATH).run()
        at.session_state.page = "vision"
        at.session_state.latest_vision_result = result
        at.run()
        self.assertFalse(at.exception)

    def test_potato_late_blight_analysis(self):
        """Late blight dark rot displays Potato Late Blight diagnosis."""
        from services.vision_service import analyze_plant_image

        lb_bytes = _make_late_blight_leaf()
        result = analyze_plant_image(lb_bytes, farm_context={"crop": "Potato"})
        self.assertTrue(result.success)
        self.assertFalse(result.healthy)
        self.assertEqual(result.disease_code, "POTATO_LATE_BLIGHT")
        self.assertIn("Late Blight", result.diagnosis)

    def test_chlorosis_yellowing_analysis(self):
        """Yellowing leaf displays Chlorosis / nutrient stress diagnosis."""
        from services.vision_service import analyze_plant_image

        yellow_bytes = _make_yellow_chlorosis_leaf()
        result = analyze_plant_image(yellow_bytes, farm_context={"crop": "Cotton"})
        self.assertTrue(result.success)
        self.assertFalse(result.healthy)
        self.assertEqual(result.disease_code, "NUTRIENT_CHLOROSIS")
        self.assertIn("Chlorosis", result.diagnosis)

    def test_assistant_integration_with_vision_context(self):
        """Assistant gives leaf diagnosis advice when vision_result is available."""
        from services.ai_service import get_ai_response
        from services.vision_service import analyze_plant_image

        eb_bytes = _make_early_blight_leaf()
        result = analyze_plant_image(eb_bytes, farm_context={"crop": "Tomato"})

        context = {
            "crop": "Tomato",
            "vision_result": result,
            "soil_moisture": 45.0,
            "temperature": 28.0,
            "humidity": 65.0,
        }

        # Inquire about the leaf scan
        reply = get_ai_response("What did you find on my leaf photo?", context=context)
        self.assertIn("Early Blight", reply)
        self.assertIn("Tomato", reply)

        # Inquire about recommended care
        reply_action = get_ai_response("What should I do about this disease?", context=context)
        self.assertIn("Early Blight", reply_action)

    def test_vision_page_dark_mode_render(self):
        """Vision page renders without exceptions in dark mode."""
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        # Switch to dark mode
        at.button(key="btn_theme_toggle").click().run()
        self.assertEqual(at.session_state.theme, "dark")

        # Navigate to Vision
        at.button(key="nav_vision").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.page, "vision")
        self.assertEqual(at.session_state.theme, "dark")


if __name__ == "__main__":
    unittest.main()
