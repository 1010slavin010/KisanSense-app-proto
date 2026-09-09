"""Backward-compatibility alias for utils.translations."""

from utils.translations import (
    DEFAULT_LANG,
    SUPPORTED_LANGUAGES,
    TRANSLATIONS,
    get_current_lang,
    t,
)

__all__ = ["DEFAULT_LANG", "SUPPORTED_LANGUAGES", "TRANSLATIONS", "get_current_lang", "t"]
