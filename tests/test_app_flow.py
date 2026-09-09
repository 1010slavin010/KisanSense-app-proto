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


    def test_home_simulation_conditions(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        # Set DRY condition
        at.session_state.sim_condition = "DRY"
        at.session_state.sensor_reading = None
        at.run()
        self.assertFalse(at.exception)
        # Should have a water needed warning
        self.assertTrue(len(at.warning) > 0)
        self.assertIn("Irrigation is advised", at.warning[0].value)

        # Set SENSOR_OFFLINE condition
        at.session_state.sim_condition = "SENSOR_OFFLINE"
        at.session_state.sensor_reading = None
        at.run()
        self.assertFalse(at.exception)
        # Should have an offline error alert
        self.assertTrue(len(at.error) > 0)
        self.assertIn("offline", at.error[0].value.lower())

    def test_chatbot_telemetry_queries(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        # 1. Query online sensor status
        at.session_state.sim_condition = "NORMAL"
        at.session_state.sensor_reading = None
        at.run()
        at.chat_input[0].set_value("Is my sensor working?").run()
        self.assertFalse(at.exception)
        reply = at.session_state.chat_messages[-1]["content"]
        self.assertIn("online", reply.lower())

        # 2. Query with offline sensor
        at.session_state.sim_condition = "SENSOR_OFFLINE"
        at.session_state.sensor_reading = None
        at.run()
        at.chat_input[0].set_value("Should I water my plants?").run()
        self.assertFalse(at.exception)
        reply_offline = at.session_state.chat_messages[-1]["content"]
        self.assertIn("offline", reply_offline.lower())

    def test_hardware_telemetry_flow(self):
        from services.hardware_client import HardwareClient
        from services.telemetry_store import GLOBAL_TELEMETRY_STORE

        GLOBAL_TELEMETRY_STORE.clear()
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        # 1. Switch to hardware mode with empty store -> offline
        at.session_state.telemetry_mode = "hardware"
        at.session_state.sensor_reading = None
        at.run()
        self.assertFalse(at.exception)
        self.assertTrue(len(at.error) > 0)
        self.assertIn("offline", at.error[0].value.lower())

        # 2. Ingest live hardware reading
        HardwareClient.ingest({
            "device_id": "esp32-field-test",
            "soil_moisture": 42.0,
            "temperature": 27.0,
            "humidity": 60.0,
            "battery_voltage": 3.90,
            "wifi_rssi": -65,
        })
        at.session_state.sensor_reading = None
        at.run()
        self.assertFalse(at.exception)
        GLOBAL_TELEMETRY_STORE.clear()

    def test_hardware_low_battery_alert(self):
        from services.hardware_client import HardwareClient
        from services.telemetry_store import GLOBAL_TELEMETRY_STORE

        GLOBAL_TELEMETRY_STORE.clear()
        HardwareClient.ingest({
            "device_id": "esp32-field-low-batt",
            "soil_moisture": 45.0,
            "temperature": 25.0,
            "humidity": 60.0,
            "battery_voltage": 3.20,  # Below 3.4V threshold
            "wifi_rssi": -70,
        })
        at = AppTest.from_file(APP_PATH).run()
        at.session_state.telemetry_mode = "hardware"
        at.session_state.sensor_reading = None
        at.run()
        self.assertFalse(at.exception)
        # Should surface low battery warning
        self.assertTrue(len(at.warning) > 0)
        self.assertTrue(any("battery" in w.value.lower() or "3.20" in w.value for w in at.warning))
        GLOBAL_TELEMETRY_STORE.clear()


if __name__ == "__main__":
    unittest.main()

