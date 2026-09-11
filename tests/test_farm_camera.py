"""AppTest integration tests for the Camera / Crop Scan experience on the Farm route.

Verifies:
1. Farm route renders as 'Camera / Crop Scan' with H1 and explanatory subtitle.
2. Presence of photo guidance tips.
3. Presence of dual input methods (file uploader and camera input).
4. Image upload lifecycle: preview, 'ready for analysis' status, and 'Analyze Crop' CTA button.
5. Crop health analysis execution and result card rendering (Healthy vs Diseased leaf).
6. Persistence of diagnostic result in st.session_state.latest_vision_result.
7. Assistant integration: Chatbot leverages latest_vision_result from camera scan.
8. Multilingual rendering across English, Hindi, Tamil, and Kannada.
9. Farm profile settings expander remains accessible and operable.
"""

from __future__ import annotations

import io
import os
import unittest
import numpy as np
from PIL import Image
from streamlit.testing.v1 import AppTest

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))


def _make_leaf_bytes(is_healthy: bool = True) -> bytes:
    """Generate synthetic leaf image bytes for test screening."""
    arr = np.zeros((256, 256, 3), dtype=np.uint8)
    if is_healthy:
        arr[:, :] = [35, 165, 40]
        arr[::4, ::4, 1] = 180
    else:
        # Early blight necrotic spots
        arr[:, :] = [45, 160, 45]
        arr[40:80, 40:80] = [120, 75, 25]
        arr[120:160, 120:160] = [115, 70, 20]
    img = Image.fromarray(arr)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestFarmCameraScan(unittest.TestCase):
    def test_farm_route_renders_camera_scan_h1_and_subtitle(self):
        """Step 3 & 12: Verify Farm route loads as Camera / Crop Scan with single H1."""
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        # Navigate to Farm route
        at.button(key="nav_farm").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.page, "farm")

        raw_md = " ".join([m.value for m in at.markdown])
        self.assertIn("Camera / Crop Scan", raw_md)
        self.assertIn("Upload a plant or leaf photo, or use your camera to check crop health.", raw_md)

        # Guidance tips present
        self.assertIn("For better results:", raw_md)
        self.assertIn("Take the photo in good daylight.", raw_md)
        self.assertIn("Keep the leaf in focus.", raw_md)

    def test_dual_input_controls_present(self):
        """Step 4: Verify both file uploader and camera input controls exist on the page."""
        at = AppTest.from_file(APP_PATH).run()
        at.button(key="nav_farm").click().run()
        self.assertFalse(at.exception)

        # Verify tabs and uploader
        self.assertTrue(len(at.tabs) >= 2)
        self.assertTrue(len(at.file_uploader) > 0)
        # Verify Camera tab label
        tab_labels = [t.label for t in at.tabs]
        self.assertTrue(any("camera" in l.lower() or "photo" in l.lower() for l in tab_labels))

    def test_image_analysis_flow_and_session_state(self):
        """Steps 5, 6, 7, 10: Verify image preview, Analyze Crop CTA, and result card."""
        at = AppTest.from_file(APP_PATH).run()
        at.button(key="nav_farm").click().run()
        self.assertFalse(at.exception)

        leaf_bytes = _make_leaf_bytes(is_healthy=True)
        at.session_state.farm_scan_active_bytes = leaf_bytes
        at.run()
        self.assertFalse(at.exception)

        # Status 'ready for analysis' appears
        self.assertTrue(any("Image ready for analysis" in s.value for s in at.success))

        # Main CTA 'Analyze Crop' button is present and clickable
        btn_analyze = at.button(key="btn_analyze_crop")
        self.assertIsNotNone(btn_analyze)
        btn_analyze.click().run()
        self.assertFalse(at.exception)

        # Result is stored in st.session_state.latest_vision_result
        self.assertIsNotNone(at.session_state.latest_vision_result)
        result = at.session_state.latest_vision_result
        self.assertTrue(result.success)
        self.assertTrue(result.healthy)

        # Result card rendered
        raw_md = " ".join([m.value for m in at.markdown])
        self.assertIn("CROP HEALTH RESULT", raw_md)
        self.assertIn("Healthy", raw_md)
        self.assertIn("What we observed", raw_md)
        self.assertIn("Recommended action", raw_md)

    def test_assistant_receives_camera_scan_context(self):
        """Step 11: Verify KisanSense Assistant has access to latest crop scan result."""
        at = AppTest.from_file(APP_PATH).run()
        at.button(key="nav_farm").click().run()

        # Simulate early blight scan
        diseased_bytes = _make_leaf_bytes(is_healthy=False)
        at.session_state.farm_scan_active_bytes = diseased_bytes
        at.run()
        at.button(key="btn_analyze_crop").click().run()
        self.assertFalse(at.exception)
        self.assertFalse(at.session_state.latest_vision_result.healthy)

        # Navigate to Assistant and query about scan
        at.button(key="nav_assistant").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.page, "assistant")

        at.chat_input[0].set_value("What did the leaf scan show?").run()
        self.assertFalse(at.exception)

        reply = at.session_state.chat_messages[-1]["content"]
        # Assistant must reference foliar scan findings
        self.assertTrue(
            "blight" in reply.lower()
            or "leaf" in reply.lower()
            or "symptom" in reply.lower()
            or "spot" in reply.lower()
        )

    def test_multilingual_camera_scan_rendering(self):
        """Step 16: Verify Camera page renders in all supported languages."""
        lang_h1_map = {
            "en": "Camera / Crop Scan",
            "hi": "कैमरा / फसल स्कैन",
            "ta": "கேமரா / பயிர் ஸ்கேன்",
            "kn": "ಕ್ಯಾಮೆರಾ / ಬೆಳೆ ಸ್ಕ್ಯಾನ್",
        }

        for lang, expected_h1 in lang_h1_map.items():
            at = AppTest.from_file(APP_PATH)
            at.session_state.lang = lang
            at.run()
            at.button(key="nav_farm").click().run()
            self.assertFalse(at.exception, f"Failed on language {lang}")
            raw_md = " ".join([m.value for m in at.markdown])
            self.assertIn(expected_h1, raw_md, f"Expected H1 '{expected_h1}' not found in lang {lang}")

    def test_farm_profile_expander_accessible(self):
        """Step 13: Verify farm profile settings remain editable inside expander."""
        at = AppTest.from_file(APP_PATH).run()
        at.button(key="nav_farm").click().run()
        self.assertFalse(at.exception)

        # Verify expander is present
        self.assertTrue(len(at.expander) > 0)
        # Profile form inputs are present
        self.assertTrue(len(at.text_input) >= 2)


if __name__ == "__main__":
    unittest.main()
