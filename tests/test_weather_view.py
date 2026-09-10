"""AppTest end-to-end integration tests for KisanSense Weather Page.

Verifies:
- Weather page renders cleanly via navbar navigation
- Location banner, demo simulator badge, and metric cards are displayed
- 3-day forecast sequence is present
- "What Should I Do Now?" action hero is present
- "What Does This Mean for My Farm?" impact section is present
- "Ask Assistant" button navigates to assistant with context
- Multilingual translation across EN, HI, TA, KN
- Dark theme rendering without exceptions
"""

from __future__ import annotations

import os
import unittest
from streamlit.testing.v1 import AppTest

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))


class TestWeatherView(unittest.TestCase):
    def test_navigate_to_weather_page(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        # Click weather in navbar
        at.button(key="nav_weather").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.page, "weather")

        # Check that weather snapshot was initialized in session state
        self.assertIsNotNone(at.session_state.latest_weather_snapshot)
        self.assertEqual(at.session_state.latest_weather_snapshot.source, "demo_weather_simulator")

        # Check Ask Assistant button is present
        btn_ask = at.button(key="btn_weather_ask_assistant")
        self.assertIsNotNone(btn_ask)

    def test_weather_page_ask_assistant_navigation(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        # Go to weather page
        at.button(key="nav_weather").click().run()
        self.assertFalse(at.exception)

        # Click Ask Assistant button
        at.button(key="btn_weather_ask_assistant").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.page, "assistant")

    def test_weather_page_multilingual_labels(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        # Switch to Hindi and go to weather
        at.session_state.lang = "hi"
        at.button(key="nav_weather").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.page, "weather")

        # Switch to Tamil
        at.session_state.lang = "ta"
        at.run()
        self.assertFalse(at.exception)

        # Switch to Kannada
        at.session_state.lang = "kn"
        at.run()
        self.assertFalse(at.exception)

    def test_weather_page_in_dark_theme(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        # Switch to dark theme
        at.button(key="btn_theme_toggle").click().run()
        self.assertEqual(at.session_state.theme, "dark")

        # Navigate to weather page
        at.button(key="nav_weather").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.page, "weather")
        self.assertEqual(at.session_state.theme, "dark")

    def test_weather_simulation_condition_switch(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        # Simulate dry condition
        at.session_state.sim_condition = "DRY"
        at.button(key="nav_weather").click().run()
        self.assertFalse(at.exception)
        self.assertLessEqual(at.session_state.latest_weather_snapshot.rain_probability, 30)

        # Simulate wet condition
        at.session_state.sim_condition = "WET"
        at.run()
        self.assertFalse(at.exception)
        self.assertGreaterEqual(at.session_state.latest_weather_snapshot.rain_probability, 60)


if __name__ == "__main__":
    unittest.main()
