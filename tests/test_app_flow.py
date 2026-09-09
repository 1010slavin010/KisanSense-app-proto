"""AppTest end-to-end integration tests for KisanSense Phase 2.

Covers:
- Initial home render and empty profile prompt
- Multilingual switching (EN -> HI -> TA -> KN)
- Navigation across all 6 pages (Home, Farm, Irrigation, Vision, Assistant, Alerts)
- Farm profile setup, validation, and session-state persistence
- Return to Home with active farm context
- Chatbot interaction with farm context
"""

import os
import unittest
from streamlit.testing.v1 import AppTest

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))


class TestAppFlow(unittest.TestCase):
    def test_initial_home_render(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)
        # Check title and tagline
        self.assertEqual(at.session_state.page, "home")
        self.assertEqual(at.session_state.lang, "en")
        # Empty profile prompt should be visible
        self.assertTrue(len(at.info) > 0)
        self.assertIn("Set up your farm profile", at.info[0].value)

    def test_language_switching(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        # Switch to Hindi
        at.session_state.lang = "hi"
        at.run()
        self.assertFalse(at.exception)
        # Check nav button label for home in Hindi
        home_btn = at.button(key="nav_home")
        self.assertEqual(home_btn.label, "होम")

        # Switch to Tamil
        at.session_state.lang = "ta"
        at.run()
        self.assertFalse(at.exception)
        home_btn = at.button(key="nav_home")
        self.assertEqual(home_btn.label, "முகப்பு")

        # Switch to Kannada
        at.session_state.lang = "kn"
        at.run()
        self.assertFalse(at.exception)
        home_btn = at.button(key="nav_home")
        self.assertEqual(home_btn.label, "ಮುಖಪುಟ")

    def test_navigation_across_all_views(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        pages = ["farm", "irrigation", "vision", "assistant", "alerts", "home"]
        for page in pages:
            at.button(key=f"nav_{page}").click().run()
            self.assertFalse(at.exception, f"Error navigating to {page}")
            self.assertEqual(at.session_state.page, page)

    def test_farm_profile_setup_and_persistence(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        # Navigate to Farm page
        at.button(key="nav_farm").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.page, "farm")

        # Set profile in session state directly (simulating form submission)
        from services.farm_service import FarmProfile, save_farm_profile

        profile = FarmProfile(
            farmer_name="Suresh Kumar",
            farm_name="Surya Farms",
            crop="Tomato",
            crop_variety="Vaishnavi",
            growth_stage="Flowering",
            soil_type="Loamy Soil",
            farm_area=7.5,
            area_unit="Acres",
            irrigation_method="Drip Irrigation",
            location="Kolar, Karnataka",
        )
        at.session_state.farm_profile = profile.to_dict()
        at.session_state.edit_farm_profile = False
        at.run()
        self.assertFalse(at.exception)

        # Verify Farm page displays overview card with edit button
        self.assertTrue(at.button(key="btn_edit_profile"))

        # Navigate to Home page
        at.button(key="nav_home").click().run()
        self.assertFalse(at.exception)

        # Verify home page has farm context and no empty profile prompt
        self.assertEqual(len(at.info), 0)

        # Navigate to Alerts and back to verify profile data survives
        at.button(key="nav_alerts").click().run()
        self.assertFalse(at.exception)

        at.button(key="nav_home").click().run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state.farm_profile["crop"], "Tomato")

    def test_chatbot_interaction(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        # Configure farm profile
        from services.farm_service import FarmProfile
        profile = FarmProfile(
            crop="Tomato",
            growth_stage="Flowering",
            soil_type="Loamy Soil",
            irrigation_method="Drip Irrigation",
        )
        at.session_state.farm_profile = profile.to_dict()

        # Submit chat input
        at.chat_input[0].set_value("When should I water?").run()
        self.assertFalse(at.exception)

        # Verify chat messages history
        self.assertEqual(len(at.session_state.chat_messages), 2)
        self.assertEqual(at.session_state.chat_messages[0]["role"], "user")
        self.assertEqual(at.session_state.chat_messages[1]["role"], "assistant")
        reply = at.session_state.chat_messages[1]["content"]
        self.assertIn("Tomato", reply)
    def test_farm_form_interactive_submit(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        # Navigate to Farm page
        at.button(key="nav_farm").click().run()
        self.assertFalse(at.exception)

        # Submit form
        at.text_input[0].set_value("Anita Patel")  # Farmer name
        at.text_input[1].set_value("Sunrise Farm")  # Farm name
        at.selectbox[1].select("Tomato")  # Crop
        at.text_input[2].set_value("Roma VF")  # Crop variety
        at.selectbox[2].select("Flowering")  # Growth stage
        at.selectbox[3].select("Loamy Soil")  # Soil type
        at.number_input[0].set_value(6.0)  # Farm area
        at.selectbox[4].select("Acres")  # Unit
        at.selectbox[5].select("Drip Irrigation")  # Irrigation method
        at.text_input[3].set_value("Pune, Maharashtra")  # Location

        # Click 'Save Farm Profile' submit button
        at.button[-1].click().run()
        self.assertFalse(at.exception)

        # Verify saved in session state
        profile = at.session_state.farm_profile
        self.assertEqual(profile["crop"], "Tomato")
        self.assertEqual(profile["farmer_name"], "Anita Patel")
        self.assertEqual(profile["farm_name"], "Sunrise Farm")
        self.assertEqual(profile["farm_area"], 6.0)
        self.assertEqual(profile["location"], "Pune, Maharashtra")


if __name__ == "__main__":
    unittest.main()

