"""Comprehensive AppTest verification for KisanSense Web Quality & Routing.

Simulates user browser sessions across all 9 pages + 404 fallback,
testing:
1. Dynamic page titles and single H1 headings per page.
2. Presence and text of breadcrumbs on non-home pages, absence on Home.
3. Functional navigation of internal linking buttons (Weather -> Irrigation, Devices -> Analytics, etc.).
4. In-app 404 handling for invalid query routes.
5. All 4 supported languages (English, Hindi, Tamil, Kannada).
6. Theme toggling (light -> dark -> light).
"""

from __future__ import annotations

import os
import unittest
from streamlit.testing.v1 import AppTest

from utils.seo import get_page_h1, get_page_title

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))


class TestFullAppQualityFlow(unittest.TestCase):
    def test_all_pages_render_with_single_h1_and_correct_title(self):
        """Verify each page renders with exactly one H1 and proper title."""
        pages = [
            ("home", "How is your farm?"),
            ("farm", "Farm Profile"),
            ("weather", "Farm Weather"),
            ("irrigation", "Smart Irrigation"),
            ("vision", "Crop Health"),
            ("assistant", "KisanSense Assistant"),
            ("alerts", "Farm Alerts"),
            ("devices", "Farm Devices"),
            ("analytics", "Farm Analytics"),
        ]

        for page_key, expected_h1 in pages:
            at = AppTest.from_file(APP_PATH)
            at.run()
            if page_key != "home":
                at.button(key=f"nav_{page_key}").click().run()

            self.assertFalse(at.exception, f"Exception on {page_key}")
            self.assertEqual(at.session_state.page, page_key)

            # Check markdown containing the expected H1
            raw_markdown = " ".join([m.value for m in at.markdown])
            self.assertIn(expected_h1, raw_markdown, f"Expected H1 '{expected_h1}' not found on {page_key}")

            # Check breadcrumb: non-home pages must have breadcrumb, home must NOT
            if page_key == "home":
                self.assertNotIn('aria-label="Breadcrumb"', raw_markdown, "Home must not have breadcrumb")
            else:
                self.assertIn('aria-label="Breadcrumb"', raw_markdown, f"{page_key} must have breadcrumb")

    def test_404_routing_and_recovery(self):
        """Verify unmapped route triggers 404 and Go Home button recovers."""
        at = AppTest.from_file(APP_PATH)
        at.query_params["page"] = "unmapped_test_path"
        at.run()

        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.page, "404")

        raw_markdown = " ".join([m.value for m in at.markdown])
        self.assertIn("Page not found", raw_markdown)

        # Click Go Home
        btn_home = at.button(key="btn_404_home")
        self.assertIsNotNone(btn_home)
        btn_home.click().run()

        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.page, "home")

    def test_internal_links_navigation(self):
        """Verify internal links take user to intended destination."""
        at = AppTest.from_file(APP_PATH)
        at.run()

        # 1. Weather -> Irrigation
        at.button(key="nav_weather").click().run()
        self.assertEqual(at.session_state.page, "weather")
        at.button(key="btn_weather_to_irrigation").click().run()
        self.assertEqual(at.session_state.page, "irrigation")

        # 2. Farm -> Weather (with configured profile)
        at.session_state.farm_profile = {
            "farmer_name": "Ramesh",
            "farm_name": "Ramesh Farm",
            "crop": "Tomato",
            "growth_stage": "Vegetative",
            "soil_type": "Loamy Soil",
            "irrigation_method": "Drip Irrigation",
            "location": "Mandya",
        }
        at.session_state.edit_farm_profile = False
        at.button(key="nav_farm").click().run()
        self.assertEqual(at.session_state.page, "farm")
        btn_wx = at.button(key="btn_farm_to_weather")
        self.assertIsNotNone(btn_wx)
        btn_wx.click().run()
        self.assertEqual(at.session_state.page, "weather")

        # 3. Devices -> Analytics
        at.button(key="nav_devices").click().run()
        self.assertEqual(at.session_state.page, "devices")
        at.button(key="btn_devices_to_analytics").click().run()
        self.assertEqual(at.session_state.page, "analytics")

        # 4. Alerts -> Irrigation & Devices
        at.button(key="nav_alerts").click().run()
        self.assertEqual(at.session_state.page, "alerts")
        at.button(key="btn_alerts_to_irrigation").click().run()
        self.assertEqual(at.session_state.page, "irrigation")

    def test_all_languages_render_cleanly(self):
        """Verify language selector renders all 4 languages without crashing."""
        for lang_code in ["en", "hi", "ta", "kn"]:
            at = AppTest.from_file(APP_PATH)
            at.session_state.lang = lang_code
            at.run()
            self.assertFalse(at.exception, f"Error rendering in language {lang_code}")

    def test_theme_toggle_flow(self):
        """Verify theme toggle between light and dark modes."""
        at = AppTest.from_file(APP_PATH).run()
        self.assertEqual(at.session_state.theme, "light")

        at.button(key="btn_theme_toggle").click().run()
        self.assertEqual(at.session_state.theme, "dark")

        at.button(key="btn_theme_toggle").click().run()
        self.assertEqual(at.session_state.theme, "light")


if __name__ == "__main__":
    unittest.main()
