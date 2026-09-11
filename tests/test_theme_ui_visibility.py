"""Integration tests verifying theme switching, semantic CSS injection, and UI visibility across all pages."""

from __future__ import annotations

import os
import unittest
from streamlit.testing.v1 import AppTest

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))


class TestThemeUIVisibility(unittest.TestCase):
    """Verifies that both Dark and Light themes inject high-contrast tokens and all views render cleanly."""

    def test_css_tokens_defined_in_style_file(self):
        """Verify style.css defines the complete set of high-contrast semantic tokens."""
        css_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "style.css"))
        self.assertTrue(os.path.exists(css_path))

        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()

        # Check core semantic variables
        self.assertIn("--color-bg", css_content)
        self.assertIn("--color-surface", css_content)
        self.assertIn("--color-border", css_content)
        self.assertIn("--color-text", css_content)
        self.assertIn("--color-text-secondary", css_content)
        self.assertIn("--color-text-muted", css_content)
        self.assertIn("--color-primary", css_content)
        self.assertIn("--color-accent", css_content)
        self.assertIn("--ks-text-secondary", css_content)

        # Check Streamlit component overrides
        self.assertIn('data-testid="stFileUploaderDropzone"', css_content)
        self.assertIn('data-testid="stCameraInput"', css_content)
        self.assertIn('data-testid="stTabs"', css_content)
        self.assertIn('data-testid="baseButton-primary"', css_content)
        self.assertIn('st-key-nav_', css_content)

    def test_dark_mode_css_injection(self):
        """Verify Dark Theme injects high-contrast tokens and does not omit --color-text-secondary."""
        at = AppTest.from_file(APP_PATH)
        at.run()
        self.assertFalse(at.exception)

        # Toggle to dark theme
        at.session_state.theme = "dark"
        at.run()
        self.assertFalse(at.exception)

        # Inspect injected markdown styles
        all_styles = " ".join([m.value for m in at.markdown if "<style>" in m.value])
        self.assertIn("--color-text-secondary: #CBD5E1", all_styles)
        self.assertIn("--color-text: #F8FAFC", all_styles)
        self.assertIn("--color-surface: #162723", all_styles)
        self.assertIn("--color-bg: #0F1916", all_styles)
        self.assertIn("--color-primary: #10B981", all_styles)
        self.assertIn("--color-accent: #34D399", all_styles)

    def test_all_major_pages_render_under_both_themes(self):
        """Verify all 8 main pages render without exceptions in both light and dark themes."""
        pages = ["home", "farm", "weather", "irrigation", "assistant", "alerts", "devices", "analytics"]

        for theme in ["dark", "light"]:
            for page in pages:
                at = AppTest.from_file(APP_PATH)
                at.run()
                self.assertFalse(at.exception)

                at.session_state.theme = theme
                at.session_state.page = page
                at.run()
                self.assertFalse(at.exception, f"Error rendering page '{page}' under theme '{theme}'")
                self.assertEqual(at.session_state.page, page)

    def test_camera_scan_page_elements_under_dark_theme(self):
        """Verify Camera / Crop Scan page retains all required elements in dark theme."""
        at = AppTest.from_file(APP_PATH)
        at.run()

        at.session_state.theme = "dark"
        at.session_state.page = "farm"
        at.run()
        self.assertFalse(at.exception)

        raw_text = " ".join([m.value for m in at.markdown])
        # Title and subtitle
        self.assertIn("Camera / Crop Scan", raw_text)
        self.assertIn("Upload a plant or leaf photo, or use your camera to check crop health.", raw_text)
        # Guidance tips
        self.assertIn("For better results:", raw_text)
        # Dual tabs
        tab_labels = [t.label for t in at.tabs]
        self.assertTrue(any("upload" in l.lower() for l in tab_labels))
        self.assertTrue(any("camera" in l.lower() for l in tab_labels))
        # Dual tabs and file uploader present
        self.assertTrue(len(at.tabs) >= 2)
        self.assertTrue(len(at.file_uploader) > 0)
        self.assertTrue(any("camera" in l.lower() or "photo" in l.lower() for l in tab_labels))


if __name__ == "__main__":
    unittest.main()
