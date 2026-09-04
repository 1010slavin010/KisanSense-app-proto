"""Phase 1 mock AI assistant service.

IMPORTANT: this does not call a real AI model. Keyword matching is
used only to make the Phase 1 chat UI testable end-to-end. The
function signature is intentionally stable so components/pages will
not need to change when a real LLM is connected in a later phase.
"""

from __future__ import annotations


def get_ai_response(message: str, context: dict | None = None) -> str:
    """Return a mock reply for the given user message.

    context is reserved for future use (farm profile, locale, sensor
    snapshot, etc.) and is accepted now so the signature does not need
    to change when a real AI service is wired in.
    """
    text = message.lower()
    context = context or {}

    if any(keyword in text for keyword in ("water", "irrigat", "dry")):
        return (
            "Water when soil moisture drops below 30%. Check the Irrigation "
            "card above for your current reading before you decide."
        )
    if any(keyword in text for keyword in ("soil", "moisture")):
        return (
            "Soil moisture between 30% and 60% is generally healthy for "
            "most crops. Readings below that usually call for irrigation."
        )
    if any(keyword in text for keyword in ("temperature", "hot", "cold", "heat")):
        return (
            "Most crops do well between 15°C and 35°C. Outside that range, "
            "consider shade cover or other protective measures."
        )
    if any(keyword in text for keyword in ("disease", "leaf", "pest", "spot")):
        return (
            "Plant disease detection isn't available yet — it's planned for "
            "a later update. For now, isolate affected plants and keep an eye on them."
        )
    if any(keyword in text for keyword in ("hello", "hi", "hey")):
        return "Hello! Ask me about your soil, water or temperature and I'll do my best to help."

    return (
        "I'm a placeholder assistant for now — full AI-powered advice is "
        "coming in a future update. Try asking about soil, water, or temperature."
    )
