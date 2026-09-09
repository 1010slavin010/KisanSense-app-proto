"""AI assistant service for KisanSense.

Provides farmer-aware and telemetry-aware agricultural advisory.
Answers inquiries referencing live/simulated sensor readings (soil moisture,
temperature, humidity, connectivity) alongside farm context (crop, soil type,
growth stage, irrigation method). Strictly avoids fabricating values or missing data.
"""

from __future__ import annotations

from typing import Any


def get_ai_response(message: str, context: dict[str, Any] | None = None) -> str:
    """Return an intelligent, farm- and telemetry-aware reply.

    context accepts:
      - farm profile attributes (crop, soil_type, growth_stage, irrigation_method, location, etc.)
      - sensor telemetry (soil_moisture, temperature, humidity, sensor_online, last_updated, etc.)
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

    # Telemetry attributes
    soil_moisture = ctx.get("soil_moisture")
    temperature = ctx.get("temperature")
    humidity = ctx.get("humidity")
    sensor_online = ctx.get("sensor_online", True)
    last_updated = ctx.get("last_updated", "")

    # Construct descriptive crop descriptor if available
    crop_desc = f"**{crop}**" if crop else "your crop"
    if crop and variety:
        crop_desc = f"**{crop} ({variety})**"

    # 1. Sensor status and connectivity inquiries
    if any(keyword in text for keyword in ("sensor working", "sensor online", "sensor offline", "sensor status", "is my sensor", "telemetry")):
        if not sensor_online:
            return (
                "Your farm sensor probe is currently **offline** or disconnected. "
                "Real-time telemetry is unavailable. Please inspect the device wiring, power supply, and probe contact."
            )
        readings_summary = []
        if soil_moisture is not None:
            readings_summary.append(f"Soil Moisture: {soil_moisture:.0f}%")
        if temperature is not None:
            readings_summary.append(f"Temperature: {temperature:.0f}°C")
        if humidity is not None:
            readings_summary.append(f"Air Humidity: {humidity:.0f}%")

        details_str = f" ({', '.join(readings_summary)})" if readings_summary else ""
        time_str = f" as of {last_updated}" if last_updated else ""
        return f"Your farm sensor is currently **online and transmitting normally**{time_str}{details_str}."

    # 2. Irrigation & Water inquiries
    if any(keyword in text for keyword in ("water", "irrigat", "dry", "moisture")):
        if any(keyword in text for keyword in ("soil", "ground")) and not any(kw in text for kw in ("water", "irrigat", "dry", "should i")):
            # Soil-specific below
            pass
        else:
            # Check offline status first
            if not sensor_online:
                return (
                    f"Your soil sensor is currently **offline**, so real-time moisture telemetry is unavailable for {crop_desc}. "
                    "Please inspect the sensor connection and check field soil moisture manually before turning on irrigation."
                )

            # Telemetry-aware answer
            if soil_moisture is not None:
                if soil_moisture < 30.0:
                    advice = (
                        f"Your current soil moisture is **{soil_moisture:.0f}%**, which is below the 30% healthy threshold for {crop_desc}. "
                        "**Irrigation is recommended now** to prevent water stress."
                    )
                    if stage:
                        advice += f" Consistent moisture is especially critical during the **{stage}** stage."
                    if irrigation:
                        advice += f" Use your {irrigation} system to apply water uniformly."
                    return advice
                elif soil_moisture <= 60.0:
                    advice = (
                        f"Your current soil moisture is **{soil_moisture:.0f}%**, which is within the healthy range (30%–60%) for {crop_desc}. "
                        "**Irrigation is not required** at this moment."
                    )
                    return advice
                else:
                    return (
                        f"Your current soil moisture is **{soil_moisture:.0f}%**, indicating wet soil. "
                        "**Do not irrigate**, as excessive moisture can lead to root aeration issues or fungal risks."
                    )

            # Fallback if no telemetry
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
                    f"{prefix}, maintain soil moisture between 30% and 60%. "
                    f"Check the Irrigation card above for your current sensor reading before turning on water."
                )
            return (
                "Water when soil moisture drops below 30%. Check the Irrigation "
                "card above for your current reading before you decide."
            )

    # 3. Soil health and type
    if any(keyword in text for keyword in ("soil", "clay", "loam", "sand", "earth")):
        moist_str = f" Current moisture reading is **{soil_moisture:.0f}%**." if soil_moisture is not None and sensor_online else ""
        if not sensor_online:
            moist_str = " (Note: Soil sensor is currently offline)."

        if soil and crop:
            return (
                f"Your farm is growing {crop_desc} in **{soil}**.{moist_str} "
                f"Maintaining moisture between 30% and 60% ensures healthy aeration and nutrient uptake."
            )
        if soil:
            return (
                f"Your farm soil is configured as **{soil}**.{moist_str} "
                "Soil moisture between 30% and 60% is generally healthy."
            )
        if crop:
            return (
                f"For healthy {crop_desc} growth, maintain soil moisture between 30% and 60%.{moist_str}"
            )
        return (
            f"Soil moisture between 30% and 60% is generally healthy for most crops.{moist_str}"
        )

    # 4. Temperature, Humidity & Weather
    if any(keyword in text for keyword in ("temperature", "temp", "hot", "cold", "heat", "weather", "humidity")):
        if not sensor_online:
            return f"Temperature and humidity telemetry are currently unavailable because your sensor is offline."

        temp_str = f"**{temperature:.0f}°C**" if temperature is not None else "normal"
        hum_str = f" with **{humidity:.0f}%** air humidity" if humidity is not None else ""
        loc_str = f" in {location}" if location else ""

        if crop:
            return (
                f"Current field temperature for {crop_desc}{loc_str} is {temp_str}{hum_str}. "
                f"Most varieties thrive between 15°C and 35°C. "
                f"{'Temperatures are elevated — consider shade or timely watering.' if temperature and temperature > 35 else 'Conditions are currently comfortable.'}"
            )
        return f"Current farm temperature is {temp_str}{hum_str}. Most crops do best between 15°C and 35°C."

    # 5. Disease / Vision / Pests
    if any(keyword in text for keyword in ("disease", "leaf", "pest", "spot", "bug", "fungus")):
        crop_mention = f" for {crop_desc}" if crop else ""
        return (
            f"Plant disease detection{crop_mention} isn't available yet — it's planned for "
            f"a later update in the Vision tab. For now, isolate affected plants and check soil drainage."
        )

    # 6. Greetings
    if any(keyword in text for keyword in ("hello", "hi", "hey", "namaste", "vanakkam", "namaskara")):
        greeting = f"Hello {farmer}!" if farmer else "Hello!"
        sensor_status_note = ""
        if not sensor_online:
            sensor_status_note = " (Note: Your soil probe appears to be offline.)"
        if crop:
            return f"{greeting} I see you are cultivating {crop_desc}.{sensor_status_note} How can I assist with your watering, soil, or crops today?"
        return f"{greeting}{sensor_status_note} Ask me about your soil, water or temperature and I'll do my best to help."

    # 7. Farm summary inquiry
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
            if soil_moisture is not None and sensor_online:
                details.append(f"Current Moisture: {soil_moisture:.0f}%")
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
