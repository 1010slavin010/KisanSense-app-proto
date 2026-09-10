"""Test suite validating the final chatbot UI integration on the Home page."""

import os
import unittest
from streamlit.testing.v1 import AppTest

APP_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "app.py"))


class TestChatbotFinalUI(unittest.TestCase):
    """Verify the integrated charcoal-green assistant panel and chatbot behavior."""

    def test_home_page_chatbot_renders_and_has_chips(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        # 4 prompt chips must be present
        chip_buttons = [b for b in at.button if b.key and b.key.startswith("chip_home_")]
        self.assertEqual(len(chip_buttons), 4, "Expected 4 prompt chips on home page")

        # Chat input must be present with the localized placeholder
        self.assertGreaterEqual(len(at.chat_input), 1, "Chat input missing on home page")
        self.assertEqual(at.chat_input[0].placeholder, "Type your question...")

    def test_chatbot_submission_flow(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        at.chat_input[0].set_value("Should I water my crop?").run()
        self.assertFalse(at.exception)

        self.assertEqual(len(at.session_state.chat_messages), 2)
        self.assertEqual(at.session_state.chat_messages[0]["role"], "user")
        self.assertEqual(at.session_state.chat_messages[1]["role"], "assistant")
        self.assertTrue(len(at.session_state.chat_messages[1]["content"]) > 0)

    def test_chatbot_chip_quick_query(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        chips = [b for b in at.button if b.key and b.key.startswith("chip_home_")]
        chips[0].click().run()
        self.assertFalse(at.exception)

        self.assertEqual(len(at.session_state.chat_messages), 2)
        self.assertEqual(at.session_state.chat_messages[0]["role"], "user")
        self.assertEqual(at.session_state.chat_messages[1]["role"], "assistant")

    def test_chatbot_in_dark_mode(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        # Toggle to dark mode
        at.button(key="btn_theme_toggle").click().run()
        self.assertEqual(at.session_state.theme, "dark")
        self.assertFalse(at.exception)

        # Chatbot interaction in dark mode
        at.chat_input[0].set_value("How is my soil?").run()
        self.assertFalse(at.exception)
        self.assertEqual(len(at.session_state.chat_messages), 2)
        self.assertEqual(at.session_state.theme, "dark")

    def test_chatbot_multilingual_labels(self):
        at = AppTest.from_file(APP_PATH).run()
        self.assertFalse(at.exception)

        # Switch to Hindi
        at.selectbox(key="lang_selector").select("hi").run()
        self.assertEqual(at.session_state.lang, "hi")
        self.assertFalse(at.exception)
        self.assertEqual(at.chat_input[0].placeholder, "अपना प्रश्न लिखें...")


if __name__ == "__main__":
    unittest.main()
