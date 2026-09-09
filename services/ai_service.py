"""AI assistant service for KisanSense.

Mock assistant implementation supporting farm-profile context.
Maintains a stable get_ai_response(message, context) signature for seamless
transition to real LLMs in future phases while leveraging current farm context.
"""

from __future__ import annotations

from typing import Any


def get_ai_response(message: str, context: dict[str, Any] | None = None) -> str:
    """Return a farm-aware reply for the given user message.

    context accepts farm profile attributes (crop, soil_type, growth_stage,
    irrigation_method, location, etc.). Only information actually present
    in context is referenced — missing information is never fabricated.
    """
    text = message.lower()
    ctx = context or {}

    crop = ctx.get("crop")
    variety = ctx.get("crop_variety")
    stage = ctx.get("growth_stage")
    soil = ctx.get("soil_type")
    irrigation = ctx.get("irrigation_method")
    location = ctx.get("location")
    farmer = ctx.get("farmer_name")

    # Construct descriptive crop descriptor if available
    crop_desc = f"**{crop}**" if crop else ""
    if crop and variety:
        crop_desc = f"**{crop} ({variety})**"

    # 1. Irrigation & Water inquiries
    if any(keyword in text for keyword in ("water", "irrigat", "dry", "moisture")):
        if any(keyword in text for keyword in ("soil", "ground")) and not any(kw in text for kw in ("water", "irrigat", "dry")):
            # Soil-specific below
            pass
        else:
            advice_parts = []
            if crop:
                if stage:
                    advice_parts.append(f"For your {crop_desc} at **{stage}** stage")
                else:
                    advice_parts.append(f"For your {crop_desc}")

                if soil:
                    advice_parts.append(f"in **{soil}**")
                if irrigation:
                    advice_parts.append(f"using {irrigation}")

                prefix = " ".join(advice_parts)
                return (
                    f"{prefix}, consistent moisture is essential for strong root development and yield. "
                    f"Maintain soil moisture between 30% and 60%. "
                    f"Check the Irrigation card above for your current sensor reading before turning on water."
                )
            return (
                "Water when soil moisture drops below 30%. Check the Irrigation "
                "card above for your current reading before you decide."
            )

    # 2. Soil health and type
    if any(keyword in text for keyword in ("soil", "clay", "loam", "sand", "earth")):
        if soil and crop:
            return (
                f"Your farm is growing {crop_desc} in **{soil}**. "
                f"Soil moisture between 30% and 60% provides healthy aeration and nutrient uptake. "
                f"Readings below that usually call for irrigation."
            )
        if soil:
            return (
                f"Your farm is registered with **{soil}**. "
                f"Soil moisture between 30% and 60% is generally healthy. Readings below that usually call for irrigation."
            )
        if crop:
            return (
                f"For healthy {crop_desc} growth, maintain soil moisture between 30% and 60%. "
                f"Readings below 30% indicate stress and require irrigation."
            )
        return (
            "Soil moisture between 30% and 60% is generally healthy for "
            "most crops. Readings below that usually call for irrigation."
        )

    # 3. Temperature & Weather
    if any(keyword in text for keyword in ("temperature", "hot", "cold", "heat", "weather")):
        loc_str = f" in {location}" if location else ""
        if crop:
            return (
                f"For your {crop_desc}{loc_str}, most crops thrive between 15°C and 35°C. "
                f"If temperatures rise above 35°C, consider mulching or timely irrigation to reduce heat stress."
            )
        return (
            "Most crops do well between 15°C and 35°C. Outside that range, "
            "consider shade cover or other protective measures."
        )

    # 4. Disease / Vision / Pests
    if any(keyword in text for keyword in ("disease", "leaf", "pest", "spot", "bug", "fungus")):
        crop_mention = f" for {crop_desc}" if crop else ""
        return (
            f"Plant disease detection{crop_mention} isn't available yet — it's planned for "
            f"a later update in the Vision tab. For now, isolate affected plants and check soil drainage."
        )

    # 5. Greetings
    if any(keyword in text for keyword in ("hello", "hi", "hey", "namaste", "vanakkam", "namaskara")):
        greeting = f"Hello {farmer}!" if farmer else "Hello!"
        if crop:
            return f"{greeting} I see you are cultivating {crop_desc}. How can I assist with your watering, soil, or crops today?"
        return f"{greeting} Ask me about your soil, water or temperature and I'll do my best to help."

    # 6. Farm summary inquiry
    if any(keyword in text for keyword in ("my farm", "farm details", "what crop", "profile")):
        if crop:
            details = [f"Crop: {crop_desc}"]
            if stage:
                details.append(f"Stage: {stage}")
            if soil:
                details.append(f"Soil: {soil}")
            if irrigation:
                details.append(f"Irrigation: {irrigation}")
            if location:
                details.append(f"Location: {location}")
            return f"Here is your active farm context: {', '.join(details)}. Ask me anytime about irrigation or crop care!"
        return "You have not set up your farm profile yet. Head over to the Farm tab to personalize your recommendations!"

    # Default fallback
    if crop:
        return (
            f"I'm a placeholder assistant for now — full AI-powered advice tailored for your {crop_desc} is "
            f"coming in a future update. Try asking about soil, water, or temperature."
        )
    return (
        "I'm a placeholder assistant for now — full AI-powered advice is "
        "coming in a future update. Try asking about soil, water, or temperature."
    )
