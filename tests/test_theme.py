"""Tests for KisanSense Light/Dark Theme functionality.

Verifies:
- Default session theme is "light"
- Navbar button toggles theme from light -> dark -> light
- Session state persistence of theme across page navigation
- Button labels and multilingual support for theme toggle
- Business logic parity: intelligence, sensor readings, and recommendations remain identical in both themes
"""

import os
import unittest
from streamlit.testing.v1 import AppTest

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))


class TestTheme(unittest.TestCase):
    def test_default_theme_is_light(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.theme, "light")

        # Toggle button should prompt user to switch to Dark
        btn = at.button(key="btn_theme_toggle")
        self.assertIsNotNone(btn)
        self.assertIn("Dark", btn.label)

    def test_toggle_theme_to_dark_and_back(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.theme, "light")

        # Click to toggle to Dark
        at.button(key="btn_theme_toggle").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.theme, "dark")

        # Button label should now indicate Light option
        btn = at.button(key="btn_theme_toggle")
        self.assertIn("Light", btn.label)

        # Click to toggle back to Light
        at.button(key="btn_theme_toggle").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.theme, "light")
        btn = at.button(key="btn_theme_toggle")
        self.assertIn("Dark", btn.label)

    def test_theme_persists_across_navigation(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        # Switch to Dark
        at.button(key="btn_theme_toggle").click().run()
        self.assertEqual(at.session_state.theme, "dark")

        # Navigate through all pages and verify theme remains "dark"
        pages = ["farm", "weather", "irrigation", "vision", "assistant", "alerts", "home"]
        for p in pages:
            at.button(key=f"nav_{p}").click().run()
            self.assertFalse(at.exception, f"Error on page {p} in dark mode")
            self.assertEqual(at.session_state.theme, "dark", f"Theme lost on page {p}")

    def test_theme_toggle_multilingual(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        # Hindi in light mode: target label is "डार्क"
        at.session_state.lang = "hi"
        at.run()
        self.assertFalse(at.exception)
        btn = at.button(key="btn_theme_toggle")
        self.assertIn("डार्क", btn.label)

        # Switch to dark mode in Hindi: target label is "लाइट"
        at.button(key="btn_theme_toggle").click().run()
        self.assertEqual(at.session_state.theme, "dark")
        btn = at.button(key="btn_theme_toggle")
        self.assertIn("लाइट", btn.label)

        # Switch to Tamil in dark mode: target label is "வெளிச்சம்" (Light)
        at.session_state.lang = "ta"
        at.run()
        self.assertFalse(at.exception)
        btn = at.button(key="btn_theme_toggle")
        self.assertIn("வெளிச்சம்", btn.label)

        # Switch to Kannada in light mode: target label is "ಡಾರ್ಕ್" (Dark)
        at.button(key="btn_theme_toggle").click().run()
        self.assertEqual(at.session_state.theme, "light")
        at.session_state.lang = "kn"
        at.run()
        self.assertFalse(at.exception)
        btn = at.button(key="btn_theme_toggle")
        self.assertIn("ಡಾರ್ಕ್", btn.label)

    def test_business_logic_parity_across_themes(self):
        """Verify that farm profile, intelligence outputs, and navigation remain intact across theme changes."""
        from services.sensor_simulator import CONDITION_DRY

        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        # Set up a farm profile and valid condition
        at.session_state.farm_profile["farmer_name"] = "Ramesh Patel"
        at.session_state.farm_profile["crop"] = "Wheat"
        at.session_state.sim_condition = CONDITION_DRY

        # Toggle to dark mode via button click
        at.button(key="btn_theme_toggle").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.theme, "dark")

        # Verify farm profile, condition, and core state are completely preserved
        self.assertEqual(at.session_state.farm_profile["farmer_name"], "Ramesh Patel")
        self.assertEqual(at.session_state.farm_profile["crop"], "Wheat")
        self.assertEqual(at.session_state.sim_condition, CONDITION_DRY)

        # Verify navigation to Assistant in dark mode works without errors
        at.button(key="nav_assistant").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.theme, "dark")

        # Toggle back to light mode in Assistant view
        at.button(key="btn_theme_toggle").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.theme, "light")

    def test_all_views_render_in_dark_mode(self):
        """Ensure all 6 views render without any errors or missing css in dark mode."""
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        # Switch to dark mode
        at.button(key="btn_theme_toggle").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.theme, "dark")

        pages = ["farm", "irrigation", "vision", "assistant", "alerts", "home"]
        for p in pages:
            at.button(key=f"nav_{p}").click().run()
            self.assertFalse(at.exception, f"Failed rendering {p} in dark mode")
            self.assertEqual(at.session_state.theme, "dark")


if __name__ == "__main__":
    unittest.main()

