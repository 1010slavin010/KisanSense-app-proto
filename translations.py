"""Minimal translation architecture for KisanSense.

Only English ("en") is populated in Phase 1. Callers already go
through t(key) instead of hard-coded strings, so additional locales
(e.g. "ta", "kn", "ml", "tu") can be added later without touching
page or component code.
"""

from __future__ import annotations

TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "nav_home": "Home",
        "nav_farm": "Farm",
        "nav_irrigation": "Irrigation",
        "nav_vision": "Vision",
        "nav_assistant": "Assistant",
        "nav_alerts": "Alerts",
        "home_tagline": "Smart farming, made simple.",
        "home_status_active": "Farm monitoring active",
        "card_soil_title": "Soil Moisture",
        "card_temp_title": "Temperature",
        "card_irrigation_title": "Irrigation",
        "assistant_title": "Ask KisanSense",
        "assistant_subtitle": "Get simple advice about your crops, soil and irrigation.",
        "assistant_welcome": "How can I help with your farm today?",
        "assistant_placeholder": "Ask about soil, crops or irrigation...",
    }
}

DEFAULT_LANG = "en"


def t(key: str, lang: str = DEFAULT_LANG) -> str:
    """Look up a UI string, falling back to English, then the key itself."""
    locale = TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANG])
    return locale.get(key, TRANSLATIONS[DEFAULT_LANG].get(key, key))
