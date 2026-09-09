"""Unit tests for translation engine and multi-language support."""

import unittest
from utils.translations import (
    DEFAULT_LANG,
    SUPPORTED_LANGUAGES,
    TRANSLATIONS,
    t,
)
import utils.translation as compat_translation


class TestTranslations(unittest.TestCase):
    def test_supported_languages_list(self):
        self.assertIn("en", SUPPORTED_LANGUAGES)
        self.assertIn("hi", SUPPORTED_LANGUAGES)
        self.assertIn("ta", SUPPORTED_LANGUAGES)
        self.assertIn("kn", SUPPORTED_LANGUAGES)
        self.assertEqual(DEFAULT_LANG, "en")

    def test_navigation_keys_present_in_all_languages(self):
        required_keys = [
            "nav_home",
            "nav_farm",
            "nav_irrigation",
            "nav_vision",
            "nav_assistant",
            "nav_alerts",
        ]
        for lang in ("en", "hi", "ta", "kn"):
            for key in required_keys:
                translated = t(key, lang=lang)
                self.assertTrue(bool(translated), f"Missing key {key} for lang {lang}")
                self.assertNotEqual(translated, key, f"Key {key} untranslated in {lang}")

    def test_card_titles_translated(self):
        self.assertEqual(t("card_soil_title", "en"), "Soil Moisture")
        self.assertEqual(t("card_soil_title", "hi"), "मिट्टी की नमी")
        self.assertEqual(t("card_soil_title", "ta"), "மண் ஈரப்பதம்")
        self.assertEqual(t("card_soil_title", "kn"), "ಮಣ್ಣಿನ ತೇವಾಂಶ")

    def test_fallback_to_english_for_missing_keys(self):
        # Inject temporary key into English only
        TRANSLATIONS["en"]["_test_fallback_key"] = "Fallback English Text"
        try:
            # When looked up in Hindi (which does not have _test_fallback_key), it should return English text
            self.assertEqual(t("_test_fallback_key", lang="hi"), "Fallback English Text")
            self.assertEqual(t("_test_fallback_key", lang="ta"), "Fallback English Text")
            self.assertEqual(t("_test_fallback_key", lang="kn"), "Fallback English Text")
        finally:
            del TRANSLATIONS["en"]["_test_fallback_key"]

    def test_fallback_to_key_if_missing_everywhere(self):
        # When key doesn't exist anywhere, return key itself
        self.assertEqual(t("non_existent_random_key_12345", lang="en"), "non_existent_random_key_12345")
        self.assertEqual(t("non_existent_random_key_12345", lang="hi"), "non_existent_random_key_12345")

    def test_backward_compatibility_module(self):
        self.assertEqual(compat_translation.DEFAULT_LANG, "en")
        self.assertEqual(compat_translation.t("nav_home", "en"), "Home")
        self.assertIn("hi", compat_translation.SUPPORTED_LANGUAGES)


if __name__ == "__main__":
    unittest.main()
