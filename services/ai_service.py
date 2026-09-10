"""AI assistant service for KisanSense.

Provides farmer-aware, telemetry-aware, and intelligence-driven agricultural advisory.
Consumes the Smart Farm Intelligence engine (services/farm_intelligence.py) and live/simulated
sensor telemetry alongside farm profile context (crop, soil type, growth stage, irrigation method).
Strictly deterministic, explainable, and offline-capable with zero external cloud dependencies.
"""

from __future__ import annotations

import re
from typing import Any


def _normalize_text(text: str) -> str:
    """Clean and normalize farmer query text for robust matching."""
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return " ".join(cleaned.split())


def get_ai_response(message: str, context: dict[str, Any] | None = None) -> str:
    """Return an intelligent, farm- and telemetry-aware reply grounded in Farm Intelligence.

    context accepts:
      - farm profile attributes (crop, crop_variety, soil_type, growth_stage, irrigation_method, location, etc.)
      - sensor telemetry (soil_moisture, temperature, humidity, sensor_online, last_updated, etc.)
      - intelligence (FarmIntelligenceResult from evaluate_farm_intelligence)
    """
    raw_text = message.strip()
    norm_text = _normalize_text(raw_text)
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
    intel = ctx.get("intelligence")

    # If intelligence is not precomputed but sensor telemetry is provided, evaluate it
    if intel is None and (soil_moisture is not None or "reading" in ctx):
        try:
            from services.farm_intelligence import evaluate_farm_intelligence
            from services.sensor_service import SensorReading

            if "reading" in ctx and isinstance(ctx["reading"], SensorReading):
                intel = evaluate_farm_intelligence(ctx["reading"], farm_context=ctx)
            elif soil_moisture is not None:
                reading = SensorReading(
                    soil_moisture=float(soil_moisture),
                    temperature=float(temperature if temperature is not None else 25.0),
                    humidity=float(humidity if humidity is not None else 50.0),
                    is_online=bool(sensor_online),
                    last_updated=str(last_updated or ""),
                    raw_status=str(ctx.get("raw_status", "ok")),
                )
                intel = evaluate_farm_intelligence(reading, farm_context=ctx)
        except Exception:
            intel = None

    # If intelligence indicates offline, faulted, or invalid data, honor safety
    if intel and getattr(intel, "data_quality", "reliable") in ("offline", "fault"):
        sensor_online = False

    # Construct descriptive crop descriptor if available
    crop_desc = f"**{crop}**" if crop else "your crop"
    if crop and variety:
        crop_desc = f"**{crop} ({variety})**"

    # Helper: find condition from intel by category
    def _find_condition(category: str):
        if not intel or not getattr(intel, "conditions", None):
            return None
        for c in intel.conditions:
            if c.category == category:
                return c
        return None

    # =========================================================================
    # Plant Health, Leaf Disease & Vision Inquiries
    # =========================================================================
    vision_result = ctx.get("vision_result")

    # 1. "Is my plant healthy?" / "Is my leaf healthy?"
    plant_healthy_triggers = (
        "is my plant healthy",
        "is the plant healthy",
        "is my crop healthy",
        "is my leaf healthy",
        "are my plants healthy",
        "plant healthy",
        "leaf healthy",
    )
    if any(trigger in norm_text for trigger in plant_healthy_triggers):
        if vision_result is not None and getattr(vision_result, "success", False):
            if vision_result.healthy:
                return (
                    f"🌿 **Plant Health Assessment ({vision_result.crop})**:\n\n"
                    f"Based on your recent leaf screening, your {crop_desc} foliage appears healthy with vibrant green tissue "
                    f"and no significant foliar disease lesions detected (screening confidence: {vision_result.confidence*100:.0f}% - {vision_result.confidence_level}).\n\n"
                    f"💡 **Recommended Care**: {vision_result.recommended_action}"
                )
            else:
                return (
                    f"🌿 **Plant Health Assessment ({vision_result.crop})**:\n\n"
                    f"Based on the visual screening, your {crop_desc} leaf exhibits visual signs consistent with **{vision_result.diagnosis}** "
                    f"(screening confidence: {vision_result.confidence*100:.0f}% - {vision_result.confidence_level}).\n\n"
                    f"• **Observed Symptoms**: {vision_result.explanation}\n"
                    f"• **Affected Foliage Ratio**: ~{vision_result.affected_foliage_ratio * 100:.1f}%\n"
                    f"• **Urgency**: {vision_result.treatment_urgency.capitalize()}\n\n"
                    f"💡 **Recommended Action**: {vision_result.recommended_action}\n\n"
                    f"⚠️ *Note: This is an offline visual screening tool, not a certified clinical diagnosis. Inspect surrounding leaves physically.*"
                )
        else:
            return (
                f"🌿 No plant leaf has been scanned yet for {crop_desc}. "
                "Please upload or capture a photo in the **Crop Health** tab to run a visual screening for foliar diseases or nutrient stress."
            )

    # 2. "What disease might this be?" / "What disease is this?"
    disease_inquiry_triggers = (
        "what disease might this be",
        "what disease is this",
        "what disease",
        "what illness",
        "what infection",
        "what leaf disease",
        "disease might this be",
        "identify disease",
        "which disease",
    )
    if any(trigger in norm_text for trigger in disease_inquiry_triggers):
        if vision_result is not None and getattr(vision_result, "success", False):
            if not vision_result.healthy:
                symptoms_str = ", ".join(vision_result.symptoms_detected) if vision_result.symptoms_detected else "foliar discoloration"
                return (
                    f"🔍 **Visual Screening Assessment ({vision_result.crop})**:\n\n"
                    f"Visual screening suggests possible **{vision_result.diagnosis}** "
                    f"(classification code: `{vision_result.disease_code}`, category: {vision_result.category}) "
                    f"with **{vision_result.confidence_level}** confidence ({vision_result.confidence*100:.0f}%).\n\n"
                    f"• **Visual Evidence**: {vision_result.explanation}\n"
                    f"• **Identified Symptoms**: {symptoms_str}\n"
                    f"• **Action Urgency**: {vision_result.treatment_urgency.capitalize()}\n\n"
                    f"💡 **Recommended Action**: {vision_result.recommended_action}\n\n"
                    f"⚠️ *Disclaimer: Visual screening provides indicative guidance only. For high-value crops or ambiguous symptoms, please consult your local Krishi Vigyan Kendra (KVK) or agricultural extension officer.*"
                )
            else:
                return (
                    f"🔍 No disease symptoms were detected in your latest leaf scan for {crop_desc}. "
                    "The foliage appears healthy with no identifiable foliar lesions, blight spots, or chlorosis."
                )
        else:
            return (
                f"🔍 No plant leaf scan is currently available for {crop_desc}. "
                "Please upload or capture a leaf photo in the **Crop Health** tab to screen for possible foliar diseases."
            )

    # 3. "Why is my plant unhealthy?" / "Why are my leaves dying?"
    why_unhealthy_triggers = (
        "why is my plant unhealthy",
        "why is my crop unhealthy",
        "why are my plants unhealthy",
        "why is my leaf yellow",
        "why are leaves yellow",
        "why is the leaf yellow",
        "why is my crop sick",
        "why are my leaves dying",
    )
    if any(trigger in norm_text for trigger in why_unhealthy_triggers):
        if vision_result is not None and getattr(vision_result, "success", False):
            if not vision_result.healthy:
                symptoms_str = ", ".join(vision_result.symptoms_detected) if vision_result.symptoms_detected else "foliar discoloration"
                return (
                    f"🌿 **Observed Foliar Symptoms ({vision_result.crop})**:\n\n"
                    f"Visual screening detected: {vision_result.explanation}\n\n"
                    f"• **Observed Visual Evidence**: {symptoms_str} "
                    f"affecting approximately {vision_result.affected_foliage_ratio * 100:.1f}% of evaluated foliage.\n"
                    f"• **Interpretation**: Visual patterns are consistent with {vision_result.diagnosis}. This reflects visual symptom patterns rather than definitive laboratory proof.\n\n"
                    f"💡 **Next Steps**: {vision_result.recommended_action}"
                )
            else:
                soil_str = f" ({soil_moisture:.0f}%)" if soil_moisture is not None else ""
                return (
                    f"🌿 Your recent leaf scan showed healthy foliage with no visual signs of foliar disease. "
                    f"If your crop is showing signs of stress, the issue may stem from root-zone soil moisture{soil_str}, "
                    "heat stress, or soil drainage rather than foliar disease pathogens."
                )
        else:
            return (
                f"🌿 No plant leaf has been scanned yet to assess foliar health for {crop_desc}. "
                "If leaves look unhealthy or discolored, capture a photo in the **Crop Health** tab to run a visual screening, "
                "or check your soil moisture and temperature telemetry."
            )

    # =========================================================================
    # 1. Farm Health, Status & "How is my farm?" Inquiries
    # =========================================================================
    farm_health_triggers = (
        "how is my farm",
        "how is the farm",
        "how are things",
        "how is my crop",
        "crop health",
        "farm health",
        "farm condition",
        "farm conditions",
        "status of my farm",
        "current condition",
        "current conditions",
        "what are the current conditions",
        "field condition",
        "current status",
        "how is everything",
        "how are my plants",
    )
    if any(trigger in norm_text for trigger in farm_health_triggers):
        if intel:
            if getattr(intel, "data_quality", "reliable") != "reliable":
                return (
                    f"**Farm Status: {intel.primary_status}**\n\n"
                    f"{intel.overall_summary}\n\n"
                    f"⚠️ Real-time telemetry is currently **{intel.data_quality}**, so automated conclusions are suspended. "
                    "Please inspect your field sensors and verify field soil moisture manually."
                )

            metrics_items = []
            if soil_moisture is not None and sensor_online:
                metrics_items.append(f"🌱 Soil Moisture: **{soil_moisture:.0f}%**")
            if temperature is not None and sensor_online:
                metrics_items.append(f"🌡️ Temperature: **{temperature:.0f}°C**")
            if humidity is not None and sensor_online:
                metrics_items.append(f"💧 Air Humidity: **{humidity:.0f}%**")

            metrics_row = f"\n\n**Current Readings**: {' • '.join(metrics_items)}" if metrics_items else ""
            return f"**Farm Status: {intel.primary_status}**\n\n{intel.overall_summary}{metrics_row}"

        # Fallback if intelligence unavailable
        if crop:
            return f"Your farm is configured for {crop_desc}. Check sensor cards above for live telemetry."
        return "Farm conditions are being monitored. Ask about soil, water, or temperature for specific advice."

    # =========================================================================
    # 2. Action Guidance: "What should I do now?" / "What should I do today?"
    # =========================================================================
    action_triggers = (
        "what should i do",
        "what to do",
        "what should i do now",
        "what should i do today",
        "what action",
        "any action",
        "next step",
        "next steps",
        "recommendation",
        "what to do now",
        "advise me",
    )
    if any(trigger in norm_text for trigger in action_triggers):
        # If the inquiry specifically asks about a scanned leaf/disease/diagnosis:
        vision_result = ctx.get("vision_result")
        if vision_result is not None and getattr(vision_result, "success", False) and any(
            k in norm_text for k in ("about this", "disease", "diagnosis", "leaf", "blight", "spot", "chlorosis", "scan")
        ):
            return (
                f"🌿 **Recommended Action for {vision_result.diagnosis}** ({vision_result.crop}):\n\n"
                f"{vision_result.recommended_action}\n\n"
                f"*(Observed Symptoms: {vision_result.explanation})*"
            )

        if intel:
            if getattr(intel, "data_quality", "reliable") != "reliable":
                return (
                    f"**Action Required: Verify Field Sensors**\n\n"
                    f"Sensor telemetry is currently **{intel.data_quality}**. "
                    "Automated field actions are suspended for crop safety. "
                    "Please inspect your sensor probe wiring, power supply, and verify soil moisture manually."
                )

            actions = []
            # Foliar action if vision indicates symptoms
            if vision_result is not None and getattr(vision_result, "success", False) and not vision_result.healthy:
                actions.append(f"🌿 **Foliar Treatment ({vision_result.diagnosis})**: {vision_result.recommended_action}")

            # Irrigation action
            if intel.irrigation_status:
                if intel.irrigation_status.needs_water:
                    actions.append(f"💧 **Irrigation**: Water your crop. {intel.irrigation_status.detail}")
                else:
                    actions.append(f"🌱 **Irrigation**: Do not irrigate now. {intel.irrigation_status.detail}")

            # Humidity / foliar monitoring
            if humidity is not None and humidity > 75.0:
                actions.append(
                    f"👀 **Foliage Monitoring**: Air humidity is high ({humidity:.0f}%). "
                    "Keep monitoring the crop, especially for prolonged leaf wetness or signs of fungal disease."
                )

            # Additional conditions from intelligence
            for cond in intel.conditions:
                if cond.recommended_action and not any(cond.recommended_action in a for a in actions):
                    actions.append(f"💡 **{cond.title}**: {cond.recommended_action}")

            action_list = "\n".join(f"• {a}" for a in actions[:4])
            return (
                f"**Recommended Actions for Your Farm ({intel.primary_status})**:\n\n"
                f"{action_list}\n\n"
                f"{intel.overall_summary}"
            )

        return (
            "Based on standard agricultural practices: maintain soil moisture between 30% and 60%, "
            "monitor canopy foliage for pests, and check field drainage."
        )

    # =========================================================================
    # 2b. Specific Action & Soil Diagnostics Inquiries
    # =========================================================================
    # "Why is the soil dry?"
    why_dry_triggers = (
        "why is the soil dry",
        "why is soil dry",
        "why is it dry",
        "why dry soil",
    )
    if any(trigger in norm_text for trigger in why_dry_triggers):
        if not sensor_online:
            return (
                f"Your soil probe is currently **offline**, so real-time soil moisture is unavailable for {crop_desc}. "
                "Please inspect the probe connection and verify soil moisture manually."
            )
        if soil_moisture is not None:
            if soil_moisture < 30.0:
                temp_str = f" and ambient temperature is elevated ({temperature:.0f}°C)" if temperature and temperature > 30.0 else ""
                return (
                    f"🌱 **Soil Moisture Deficit ({soil_moisture:.0f}%)**:\n\n"
                    f"Topsoil and root-zone moisture has dropped below the 30% healthy threshold{temp_str}, "
                    f"indicating natural crop transpiration and surface evaporation have depleted available soil water for {crop_desc}.\n\n"
                    f"💡 **Action**: Irrigation is recommended to replenish the root zone before plant wilting occurs."
                )
            else:
                return (
                    f"🌱 Currently, your soil moisture is **{soil_moisture:.0f}%**, which is actually in the healthy range (not dry!) for {crop_desc}. "
                    "Routine monitoring is sufficient."
                )
        return "Soil moisture telemetry is currently unavailable. Check the Irrigation card for readings."

    # "Why shouldn't I irrigate?" / "Why not irrigate?" / "Why no watering?"
    why_no_water_triggers = (
        "why shouldn t i irrigate",
        "why shouldnt i irrigate",
        "why not irrigate",
        "why not water",
        "why shouldn t i water",
        "why shouldnt i water",
        "why no water",
        "why no irrigation",
    )
    if any(trigger in norm_text for trigger in why_no_water_triggers):
        if not sensor_online:
            return (
                f"⚠️ **Irrigation is held because your soil probe is offline.**\n\n"
                "KisanSense protects your field with an automatic fail-safe: automated watering is suspended whenever "
                "telemetry is unreachable or faulted to prevent accidental waterlogging."
            )
        weather_ctx = ctx.get("weather")
        rain_prob = getattr(weather_ctx, "rain_probability", 0) if weather_ctx else 0
        if rain_prob >= 60:
            return (
                f"🌧️ **Irrigation is delayed because significant rainfall is forecasted ({rain_prob}% chance).**\n\n"
                f"Holding off on watering for {crop_desc} conserves water and prevents over-saturation, root suffocation, "
                "and nutrient leaching."
            )
        if soil_moisture is not None and soil_moisture >= 30.0:
            status_word = "sufficiently wet" if soil_moisture > 60.0 else "in the optimal healthy range"
            return (
                f"🌱 **Irrigation is not required because soil moisture is currently {soil_moisture:.0f}%.**\n\n"
                f"The soil is already {status_word} (30%–60%) for {crop_desc}. "
                "Adding water now would waste resources and increase the risk of fungal root rot."
            )
        return (
            f"Irrigation decisions depend on soil moisture (threshold 30%) and rain forecasts. "
            f"Check current telemetry on the Home or Irrigation page."
        )

    # "What should I check today?"
    check_today_triggers = (
        "what should i check today",
        "what to check today",
        "daily check",
        "today checklist",
        "what should i inspect",
    )
    if any(trigger in norm_text for trigger in check_today_triggers):
        items = []
        if sensor_online and soil_moisture is not None:
            sm_state = "Needs water" if soil_moisture < 30.0 else ("Wet" if soil_moisture > 60.0 else "Optimal")
            items.append(f"1. 🌱 **Soil Moisture**: Current {soil_moisture:.0f}% ({sm_state}).")
        else:
            items.append("1. ⚠️ **Sensor Link**: Probe is offline. Inspect physical cable connection.")

        weather_ctx = ctx.get("weather")
        if weather_ctx:
            r_prob = getattr(weather_ctx, "rain_probability", 0)
            items.append(f"2. 🌤️ **Weather**: {getattr(weather_ctx, 'condition', 'Partly Cloudy')} (Rain: {r_prob}%).")
        else:
            items.append("2. 🌤️ **Weather**: Review the 3-day forecast in the Weather tab.")

        if vision_result and getattr(vision_result, "success", False):
            items.append(f"3. 🌿 **Foliar Health**: Latest screening shows {vision_result.diagnosis}.")
        else:
            items.append("3. 🌿 **Foliar Health**: Capture or upload a leaf in Crop Health to screen for early blight.")

        items_str = "\n".join(items)
        return (
            f"📋 **Daily Agronomic Checklist for {crop_desc}**:\n\n"
            f"{items_str}\n\n"
            "💡 Tap any card on your Home dashboard for detailed guidance."
        )

    # =========================================================================
    # 3. Irrigation & Water Inquiries: "Should I water my crop?", "Is irrigation required?"
    # =========================================================================

    irrigation_triggers = (
        "water",
        "irrigat",
        "irrigation",
        "should i water",
        "need water",
        "need irrigation",
        "is irrigation required",
        "does my crop need water",
        "does my crop need irrigation",
        "watering",
        "dry",
        "can i water",
        "turn on water",
    )
    # Check if this is an irrigation inquiry (excluding purely soil inquiries like "how is the soil")
    is_irrigation_query = any(trigger in norm_text for trigger in irrigation_triggers) and not (
        any(k in norm_text for k in ("soil", "ground"))
        and not any(k in norm_text for k in ("water", "irrigat", "dry", "should i", "need"))
    )

    if is_irrigation_query:
        if not sensor_online:
            return (
                f"Your soil sensor is currently **offline**, so real-time moisture telemetry is unavailable for {crop_desc}. "
                "Please inspect the sensor connection and check field soil moisture manually before turning on irrigation."
            )

        if soil_moisture is not None:
            if soil_moisture < 30.0:
                weather_ctx = ctx.get("weather")
                rain_prob = getattr(weather_ctx, "rain_probability", 0) if weather_ctx else 0
                has_rain_query = any(w in norm_text for w in ("rain", "raining", "rainy", "storm"))
                if (rain_prob >= 60 and (has_rain_query or "delay" in norm_text or "wait" in norm_text)) or (has_rain_query and rain_prob >= 50):
                    return (
                        f"⚠️ **Delay irrigation for now** for {crop_desc}. "
                        f"Even though soil moisture is low ({soil_moisture:.0f}%), significant rain is forecasted "
                        f"({rain_prob}% probability). Holding off on watering will conserve water and prevent waterlogging."
                    )
                advice = (
                    f"🌱 **Irrigation is recommended now** for {crop_desc}. "
                    f"Soil moisture is **{soil_moisture:.0f}%**, which is below the 30% healthy threshold to prevent water stress."
                )
                if stage:
                    advice += f" Consistent moisture is especially critical during the **{stage}** stage."
                if irrigation:
                    advice += f" Use your {irrigation} system to apply water uniformly."
                return advice
            elif soil_moisture <= 60.0:
                advice = (
                    f"🌱 **Irrigation is not required** at this moment. "
                    f"Soil moisture is **{soil_moisture:.0f}%**, which is within the healthy range (30%–60%) for {crop_desc}. "
                    "Avoid adding water for now and maintain regular monitoring."
                )
                return advice
            else:
                advice = (
                    f"🌱 Irrigation is not required right now. "
                    f"Soil moisture is {soil_moisture:.0f}%, so the soil is already sufficiently wet. "
                    "Avoid adding water for now and monitor the moisture again later."
                )
                if humidity is not None and humidity > 75.0:
                    advice += (
                        f"\n\n💧 Air humidity is currently {humidity:.0f}%, which is high. "
                        "Keep monitoring the crop, especially for prolonged leaf wetness or signs of fungal disease."
                    )
                return advice

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
                "Check the Irrigation card above for your current sensor reading before turning on water."
            )
        return (
            "Water when soil moisture drops below 30%. Check the Irrigation "
            "card above for your current reading before you decide."
        )

    # =========================================================================
    # 4. Humidity Inquiries: "Why is humidity high?", "Is humidity okay?"
    # =========================================================================
    humidity_triggers = (
        "humidity",
        "humid",
        "air moisture",
        "why is humidity high",
        "is humidity high",
        "is humidity okay",
        "is humidity normal",
        "canopy humidity",
    )
    if any(trigger in norm_text for trigger in humidity_triggers):
        if not sensor_online:
            return "Air humidity telemetry is currently unavailable because your sensor is offline."

        if humidity is not None:
            if humidity > 75.0:
                c_hum = _find_condition("humidity_risk") or _find_condition("compound_risk")
                rec = c_hum.recommended_action if c_hum else "Inspect foliage for signs of mildew or leaf spot, and maintain good field airflow."
                soil_note = (
                    f" Combined with high soil moisture ({soil_moisture:.0f}%), wet canopy conditions slow down plant transpiration."
                    if soil_moisture and soil_moisture > 60.0
                    else ""
                )
                return (
                    f"💧 Air humidity is currently **{humidity:.0f}%**, which is high (normal balanced range is 40%–75%)."
                    f"{soil_note} Warm, high-humidity air creates conditions favorable for fungal spore germination.\n\n"
                    f"💡 **Recommendation**: {rec}"
                )
            elif humidity < 35.0:
                return (
                    f"💧 Air humidity is currently **{humidity:.0f}%**, which is low. "
                    "Dry atmospheric air increases transpiration and causes foliage to lose moisture rapidly. "
                    "Keep a close eye on topsoil drying."
                )
            else:
                return (
                    f"💧 Air humidity is currently **{humidity:.0f}%**, which is within the balanced normal range (40%–75%). "
                    "Atmospheric moisture conditions are favorable for healthy crop transpiration."
                )

        return "Comfortable air humidity for most crops is between 40% and 75%. Check the Humidity card for current readings."

    # =========================================================================
    # 5. Temperature Inquiries: "Is the temperature okay?", "How is the temperature?"
    # =========================================================================
    temp_triggers = (
        "temperature",
        "temp",
        "is the temperature okay",
        "is temperature okay",
        "temp okay",
        "is it hot",
        "is it cold",
        "heat",
        "thermal",
    )
    if any(trigger in norm_text for trigger in temp_triggers):
        if not sensor_online:
            return "Temperature telemetry is currently unavailable because your sensor is offline."

        if temperature is not None:
            loc_str = f" in {location}" if location else ""
            if 15.0 <= temperature <= 35.0:
                return (
                    f"🌡️ Field temperature{loc_str} is currently **{temperature:.0f}°C**, "
                    f"which is within the comfortable normal range (15°C–35°C) for {crop_desc}. "
                    "Thermal conditions are favorable for steady growth."
                )
            elif temperature > 35.0:
                return (
                    f"🌡️ Field temperature{loc_str} is currently **{temperature:.0f}°C**, which is elevated above 35°C. "
                    "High temperatures increase crop water demand. Consider providing shade if feasible and irrigate during cooler morning or evening hours."
                )
            else:
                return (
                    f"🌡️ Field temperature{loc_str} is currently **{temperature:.0f}°C**, which is cool for tropical crops. "
                    "Vegetative growth may be slower during cooler periods."
                )

        return f"Current field temperature is normal for {crop_desc}. Most crops thrive between 15°C and 35°C."

    # =========================================================================
    # 6. Soil Health & Soil Type Inquiries: "How is the soil?", "What is my soil condition?"
    # =========================================================================
    soil_triggers = (
        "soil",
        "clay",
        "loam",
        "sand",
        "earth",
        "ground",
        "how is the soil",
        "how is my soil",
        "soil condition",
        "soil health",
        "soil status",
    )
    if any(trigger in norm_text for trigger in soil_triggers):
        moist_str = f" Current moisture reading is **{soil_moisture:.0f}%**." if soil_moisture is not None and sensor_online else ""
        if not sensor_online:
            moist_str = " (Note: Soil sensor is currently offline)."

        if soil_moisture is not None and sensor_online:
            if soil_moisture > 60.0:
                status_desc = f"Soil moisture is **{soil_moisture:.0f}%**, so the soil is already sufficiently wet. Avoid adding water for now to allow root aeration."
            elif soil_moisture < 30.0:
                status_desc = f"Soil moisture is low at **{soil_moisture:.0f}%**. Irrigation is recommended soon to replenish root zone moisture."
            else:
                status_desc = f"Soil moisture is healthy at **{soil_moisture:.0f}%** (optimal range 30%–60%)."

            soil_type_note = f" In **{soil}**, " if soil else " "
            return f"🌱 {status_desc}{soil_type_note}Soil condition is being actively tracked for {crop_desc}."

        if soil and crop:
            return (
                f"Your farm is growing {crop_desc} in **{soil}**.{moist_str} "
                "Maintaining moisture between 30% and 60% ensures healthy aeration and nutrient uptake."
            )
        if soil:
            return (
                f"Your farm soil is configured as **{soil}**.{moist_str} "
                "Soil moisture between 30% and 60% is generally healthy."
            )
        if crop:
            return f"For healthy {crop_desc} growth, maintain soil moisture between 30% and 60%.{moist_str}"
        return f"Soil moisture between 30% and 60% is generally healthy for most crops.{moist_str}"

    # =========================================================================
    # 7. Crop Health & Vision Screening Inquiry
    # =========================================================================
    vision_result = ctx.get("vision_result")
    vision_triggers = (
        "what did you find",
        "vision",
        "leaf photo",
        "photo scan",
        "leaf scan",
        "crop disease",
        "blight",
        "chlorosis",
        "what should i do about this",
        "leaf diagnosis",
        "leaf problem",
        "is this serious",
        "is it serious",
        "how serious",
        "is my plant healthy",
        "is my crop healthy",
        "are my plants healthy",
        "what disease might this be",
        "what disease is this",
        "what is this disease",
        "what disease",
        "why is my plant unhealthy",
        "why is my plant looking unhealthy",
        "why are my plants unhealthy",
        "why is the plant unhealthy",
    )
    is_vision_query = any(trigger in norm_text for trigger in vision_triggers) or (
        any(t in norm_text for t in ("leaf", "spot", "disease", "photo", "scan", "find"))
        and any(w in norm_text for w in ("what", "why", "is", "how", "check", "tell"))
    )
    if vision_result is not None and is_vision_query:
        if getattr(vision_result, "success", False):
            # 1. "Is my plant healthy?"
            if any(k in norm_text for k in ("is my plant healthy", "is my crop healthy", "are my plants healthy")):
                if vision_result.healthy:
                    return (
                        f"🟢 **Yes**, based on your recent leaf scan, your **{vision_result.crop}** foliage appears **healthy** "
                        f"with vibrant tissue and no significant visible disease lesions ({int(round(vision_result.confidence*100))}% confidence).\n\n"
                        f"{vision_result.explanation}\n\n"
                        f"**Recommended Care**: {vision_result.recommended_action}"
                    )
                else:
                    return (
                        f"⚠️ **Visual symptoms detected**: Screening of your **{vision_result.crop}** leaf indicates **{vision_result.diagnosis}** "
                        f"(Confidence: {vision_result.confidence_level.title()}).\n\n"
                        f"{vision_result.explanation}\n\n"
                        f"**Recommended Action**: {vision_result.recommended_action}\n\n"
                        f"*(Visual screening only. Consult your local agricultural officer / KVK for field verification.)*"
                    )

            # 2. "What disease might this be?"
            if any(k in norm_text for k in ("what disease might this be", "what disease is this", "what is this disease", "what disease")):
                if vision_result.healthy:
                    return (
                        f"🟢 Visual screening detected **no active foliar disease** on your {vision_result.crop} leaf. "
                        f"Tissue appears healthy and uniform ({int(round(vision_result.confidence*100))}% confidence)."
                    )
                else:
                    return (
                        f"⚠️ **Suspected Condition**: **{vision_result.diagnosis}**\n\n"
                        f"• **Category**: {vision_result.category.replace('_', ' ').title()}\n"
                        f"• **Screening Confidence**: {vision_result.confidence_level.title()} (~{int(round(vision_result.confidence*100))}%)\n"
                        f"• **Visual Evidence**: {vision_result.explanation}\n\n"
                        f"🌱 **Recommended Guidance**: {vision_result.recommended_action}\n\n"
                        f"*(Note: Visual signs are consistent with this condition; field verification by an agricultural expert is recommended.)*"
                    )

            # 3. "Why is my plant unhealthy?"
            if any(k in norm_text for k in ("why is my plant unhealthy", "why is my plant looking unhealthy", "why are my plants unhealthy", "why is the plant unhealthy")):
                if vision_result.healthy:
                    return (
                        f"🌿 Your recent leaf screening showed **healthy foliage** for {vision_result.crop}. "
                        "No visible foliar lesions were observed. If field plants appear stressed, "
                        "check root-zone soil moisture and temperature telemetry."
                    )
                else:
                    return (
                        f"🔍 **Visual Screening Observations for {vision_result.crop}**:\n\n"
                        f"• **Suspected Pattern**: {vision_result.diagnosis} (Confidence: {vision_result.confidence_level.title()})\n"
                        f"• **Observed Symptoms**: {vision_result.explanation}\n\n"
                        f"💡 **Recommended Action**: {vision_result.recommended_action}\n\n"
                        f"*(Visual screening indicates symptoms consistent with this condition; physical field inspection is recommended.)*"
                    )

            if any(k in norm_text for k in ("is this serious", "is it serious", "how serious")):
                if vision_result.healthy:
                    return (
                        f"🟢 No, it does not appear serious. Your **{vision_result.crop}** foliage shows healthy green tissue "
                        "with no significant visible disease symptoms."
                    )
                else:
                    return (
                        f"⚠️ For your **{vision_result.crop}**, {vision_result.diagnosis} warrants prompt attention. "
                        f"{vision_result.explanation}\n\n"
                        f"**Immediate Action**: {vision_result.recommended_action}"
                    )

            if vision_result.healthy:
                return (
                    f"🌿 **Crop Health Assessment ({vision_result.crop})**:\n\n"
                    f"Based on your recent visual scan, the foliage appears **healthy** with no visible signs of active disease. "
                    f"{vision_result.explanation}\n\n"
                    f"**Recommended Care**: {vision_result.recommended_action}"
                )
            else:
                conf_pct = int(round(vision_result.confidence * 100))
                return (
                    f"⚠️ **Crop Health Assessment ({vision_result.crop})**:\n\n"
                    f"**Observation**: {vision_result.diagnosis} (Confidence: {vision_result.confidence_level.title()}, ~{conf_pct}%)\n\n"
                    f"**Details**: {vision_result.explanation}\n\n"
                    f"**Action Recommended**: {vision_result.recommended_action}\n\n"
                    f"*(Note: Visual screening only. Consult your local agricultural extension officer for field verification.)*"
                )
        else:
            return (
                f"📷 **Photo Screening**: Your recent leaf photo could not be reliably diagnosed because: {vision_result.explanation}\n\n"
                f"**Tip**: {vision_result.recommended_action}"
            )
    elif vision_result is None and (
        is_vision_query
        or any(trigger in norm_text for trigger in ("what did you find", "leaf photo", "photo scan", "leaf scan", "is my plant healthy", "what disease might this be", "why is my plant unhealthy"))
    ):
        return (
            f"🌿 You haven't scanned a crop leaf yet in this session. "
            f"Head over to the **Vision (Crop Health)** tab and upload or capture a photo of your {crop_desc} leaf in natural daylight for an instant local screening!"
        )

    # =========================================================================
    # 8. Crop Risk, Disease & Foliage Monitoring: "Is my crop at risk?", "Any risks?"
    # =========================================================================
    risk_triggers = (
        "at risk",
        "crop at risk",
        "is my crop at risk",
        "any risk",
        "any risks",
        "threat",
        "danger",
        "disease",
        "leaf",
        "pest",
        "spot",
        "bug",
        "fungus",
        "mildew",
    )
    if any(trigger in norm_text for trigger in risk_triggers):
        risk_notes = []
        if intel and intel.conditions:
            for c in intel.conditions:
                if c.severity in ("critical", "alert", "warning"):
                    risk_notes.append(f"• **{c.title}**: {c.explanation} {c.recommended_action}")

        if risk_notes:
            risk_summary = "\n".join(risk_notes[:3])
            return (
                f"⚠️ **Farm Risk Assessment for {crop_desc}**:\n\n"
                f"{risk_summary}\n\n"
                "💡 **Agronomic Guidance**: Consider checking the leaves for any symptoms. "
                "If you observe spots or discoloration, isolate affected plants and ensure good airflow. "
                "You can also upload a leaf photo in the Vision tab for detailed visual inspection."
            )

        # If no active critical/warning risks
        hum_note = f" Air humidity is currently {humidity:.0f}%." if humidity is not None else ""
        return (
            f"✅ No acute climate or moisture risks are currently detected for {crop_desc}.{hum_note} "
            "Conditions appear stable. Continue regular crop monitoring and check leaves periodically for healthy foliage."
        )

    # =========================================================================
    # 8. Sensor Connectivity & Hardware Status
    # =========================================================================
    sensor_triggers = (
        "sensor working",
        "sensor online",
        "sensor offline",
        "sensor status",
        "is my sensor",
        "telemetry",
    )
    if any(trigger in norm_text for trigger in sensor_triggers):
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

    # =========================================================================
    # 9. Weather, Rain, Spraying & Field Operations
    # =========================================================================
    weather_inquiry_triggers = (
        "weather",
        "forecast",
        "climate",
        "rain",
        "raining",
        "rainfall",
        "precipitation",
        "will it rain",
        "is it going to rain",
        "spray",
        "spraying",
        "pesticide",
        "fungicide",
        "wind",
        "wind speed",
        "et0",
        "evapotranspiration",
        "solar radiation",
    )
    if any(trigger in norm_text for trigger in weather_inquiry_triggers):
        weather_obj = ctx.get("weather")
        if weather_obj is None:
            try:
                from services.weather_service import get_weather_snapshot
                weather_obj = get_weather_snapshot(
                    location=location or "Mandya, Karnataka",
                    condition_hint=ctx.get("sensor_condition", "NORMAL"),
                )
            except Exception:
                weather_obj = None

        if weather_obj is None or not getattr(weather_obj, "is_available", True):
            loc_disp = f" for **{location}**" if location else ""
            return (
                f"🌤️ Weather forecast information is currently unavailable{loc_disp}. "
                "Unable to retrieve current rain probability or microclimate conditions. "
                "Please verify your location in the Farm tab."
            )

        wind_spd = getattr(weather_obj, "wind_speed_kmh", 0.0)
        rain_prob = getattr(weather_obj, "rain_probability", 0)
        rain_mm = getattr(weather_obj, "precipitation_mm", 0.0)
        cond = getattr(weather_obj, "condition", "Partly Cloudy")
        temp = getattr(weather_obj, "temperature_c", 25.0)
        hum = getattr(weather_obj, "humidity", 50.0)
        loc_str = f" for **{weather_obj.location}**" if weather_obj and weather_obj.location else ""

        # Spraying & field operations
        if any(k in norm_text for k in ("spray", "spraying", "pesticide", "fungicide")):
            if wind_spd > 20.0 or rain_prob >= 50:
                return (
                    f"🚫 **Spraying is NOT advised right now** for {crop_desc}.\n\n"
                    f"• **Wind Speed**: **{wind_spd:.1f} km/h** (high risk of drift)\n"
                    f"• **Rain Probability**: **{rain_prob}%** (risk of chemical wash-off)\n\n"
                    "Wait for calm weather with wind under 15 km/h and no rain forecasted."
                )
            else:
                return (
                    f"✅ **Conditions are favorable for spraying** for {crop_desc}.\n\n"
                    f"• **Wind Speed**: **{wind_spd:.1f} km/h** (calm to gentle breeze)\n"
                    f"• **Rain Probability**: **{rain_prob}%** (minimal wash-off risk)\n\n"
                    "Best practice: Spray during early morning or late evening hours for optimal leaf coverage."
                )

        # Rain & precipitation specific
        if any(k in norm_text for k in ("rain", "raining", "rainfall", "precipitation")):
            if rain_prob >= 50:
                return (
                    f"🌧️ **Rain is forecasted today**{loc_str} (Probability: **{rain_prob}%**, estimated: **{rain_mm:.1f} mm**). Condition: **{cond}**.\n\n"
                    f"• **Irrigation Impact**: Hold off on watering; rain will recharge soil moisture.\n"
                    f"• **Field Action**: Ensure field drainage channels are clear to prevent waterlogging around {crop_desc} roots."
                )
            else:
                return (
                    f"☀️ **Low probability of rain today**{loc_str} (Probability: **{rain_prob}%**, estimated: **{rain_mm:.1f} mm**). Condition: **{cond}**.\n\n"
                    f"Conditions are mostly dry. Manage irrigation according to current soil moisture readings."
                )

        # General weather & forecast
        return (
            f"🌤️ **Agrarian Weather & Microclimate Forecast{loc_str}**:\n\n"
            f"• **Condition**: {cond}\n"
            f"• **Temperature**: {temp:.1f}°C\n"
            f"• **Air Humidity**: {hum:.0f}%\n"
            f"• **Rain Probability**: {rain_prob}%\n"
            f"• **Wind Speed**: {wind_spd:.1f} km/h\n\n"
            f"💡 *Field Guidance for {crop_desc}*: Weather data is synchronized with your field sensor telemetry. "
            f"Visit the dedicated **Weather** tab to review the 3-day forecast, evapotranspiration rates, and active risk signals."
        )

    # =========================================================================
    # 10. Greetings
    # =========================================================================
    greeting_triggers = ("hello", "hi", "hey", "namaste", "vanakkam", "namaskara")
    if any(norm_text == g or norm_text.startswith(f"{g} ") for g in greeting_triggers):
        greeting = f"Hello {farmer}!" if farmer else "Hello!"
        sensor_status_note = ""
        if not sensor_online:
            sensor_status_note = " (Note: Your soil probe appears to be offline.)"
        if crop:
            return f"{greeting} I see you are cultivating {crop_desc}.{sensor_status_note} How can I assist with your watering, soil, or crops today?"
        return f"{greeting}{sensor_status_note} Ask me about your soil, water or temperature and I'll do my best to help."

    # =========================================================================
    # 10. Farm Summary / Profile Inquiry
    # =========================================================================
    profile_triggers = ("my farm", "farm details", "what crop", "profile", "what am i growing")
    if any(trigger in norm_text for trigger in profile_triggers):
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

    # =========================================================================
    # 11. Deterministic Farm-Aware Default Response (NEVER A PLACEHOLDER)
    # =========================================================================
    overview_header = f"🌾 **Farm Overview ({intel.primary_status})**" if intel else f"🌾 **Farm Overview for {crop_desc}**"
    summary_text = intel.overall_summary if intel else "Your farm telemetry and conditions are being actively monitored."

    conditions_list = []
    if sensor_online:
        if soil_moisture is not None:
            c_w = _find_condition("water_stress")
            w_status = f" ({c_w.title})" if c_w else ""
            conditions_list.append(f"• **Soil Moisture**: {soil_moisture:.0f}%{w_status}")
        if temperature is not None:
            c_t = _find_condition("heat_stress")
            t_status = f" ({c_t.title})" if c_t else ""
            conditions_list.append(f"• **Temperature**: {temperature:.0f}°C{t_status}")
        if humidity is not None:
            c_h = _find_condition("humidity_risk")
            h_status = f" ({c_h.title})" if c_h else ""
            conditions_list.append(f"• **Air Humidity**: {humidity:.0f}%{h_status}")
    else:
        conditions_list.append("• **Sensor Status**: Offline (please inspect device probe)")

    conditions_block = f"\n\n**Current Field Conditions**:\n" + "\n".join(conditions_list) if conditions_list else ""

    return (
        f"{overview_header}\n\n"
        f"{summary_text}"
        f"{conditions_block}\n\n"
        "💡 *You can ask me questions like:*\n"
        "• *'Should I water my crop?'*\n"
        "• *'How is the soil?'*\n"
        "• *'Why is humidity high?'*\n"
        "• *'Is the temperature okay?'*\n"
        "• *'What should I do now?'*"
    )
