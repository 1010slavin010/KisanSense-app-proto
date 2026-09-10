"""Weather and Climate Intelligence decision engine for KisanSense.

Translates meteorological forecasts and telemetry into actionable farm decisions.
Connects WeatherSnapshots, SensorReadings, FarmProfiles, and Plant Vision context
into clear, explainable guidance on irrigation timing, heat risk, rain impact,
and foliar disease surveillance. Operates strictly deterministically and offline.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.weather_service import WeatherSnapshot


@dataclass
class WeatherRiskSignal:
    """Discrete meteorological risk signal impacting crop or field operations."""

    category: str  # "heat_stress" | "water_stress" | "excess_rain" | "humidity_disease" | "strong_wind"
    severity: str  # "critical" | "alert" | "warning" | "info" | "good"
    title: str  # Farmer-facing headline
    explanation: str  # Plain-language meteorological context
    action: str  # Actionable agronomic next step

    @property
    def risk_type(self) -> str:
        return self.category

    @property
    def description(self) -> str:
        return self.explanation

    @property
    def mitigation(self) -> str:
        return self.action


@dataclass
class WeatherFarmInsight:
    """Authoritative structured output of the weather-to-farm decision engine."""

    overall_status: str  # "NORMAL" | "WATCH" | "ATTENTION" | "HIGH RISK"
    severity: str  # "good" | "info" | "warning" | "alert" | "critical"
    primary_message: str  # Synthesized farm impact summary
    farmer_action_headline: str  # Primary action headline (e.g. "💧 Water your crop")
    farmer_action_detail: str  # Action explanation
    irrigation_impact_label: str  # "WATER SOON" | "WAIT / DELAY" | "AVOID WATERING" | "NORMAL"
    irrigation_impact_detail: str  # How weather specifically affects irrigation
    heat_stress_risk: str  # "Low" | "Moderate" | "Elevated" | "High"
    water_stress_risk: str  # "Low" | "Moderate" | "High"
    excess_rain_risk: str  # "Low" | "Moderate" | "High"
    humidity_disease_risk: str  # "Low" | "Moderate" | "Watch" | "Elevated"
    wind_risk: str  # "Normal" | "Caution for Spraying" | "Strong Wind"
    risks: list[WeatherRiskSignal] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    confidence: str = "high"
    forecast_window: str = "Next 24–48 Hours"

    @property
    def status_type(self) -> str:
        return self.severity

    @property
    def primary_action(self) -> str:
        return self.farmer_action_headline

    @property
    def action_detail(self) -> str:
        return self.farmer_action_detail

    @property
    def crop_impact_summary(self) -> str:
        return self.primary_message

    @property
    def irrigation_guidance(self) -> str:
        return self.irrigation_impact_detail

    @property
    def crop_health_risk_summary(self) -> str:
        parts = []
        if self.humidity_disease_risk in ("Watch", "Elevated"):
            parts.append(f"Elevated foliar humidity risk ({self.humidity_disease_risk})")
        if self.heat_stress_risk in ("Elevated", "High"):
            parts.append(f"High canopy heat stress ({self.heat_stress_risk})")
        if not parts:
            return "No critical weather-related crop pathogen or temperature stress detected."
        return " · ".join(parts)

    @property
    def field_work_advisory(self) -> str:
        if "Caution" in self.wind_risk or "Strong" in self.wind_risk:
            return "Postpone spraying due to gusty wind drift."
        return "Favorable window for fieldwork, spraying, and inspection."

    @property
    def active_risks(self) -> list[WeatherRiskSignal]:
        return self.risks


def evaluate_weather_intelligence(
    weather: WeatherSnapshot,
    reading: Any | None = None,
    farm_context: dict[str, Any] | None = None,
    intel: Any | None = None,
    vision_result: Any | None = None,
) -> WeatherFarmInsight:
    """Evaluate weather signals in the context of farm telemetry and crop profile.

    Args:
        weather: Active WeatherSnapshot instance.
        reading: Optional SensorReading from services.sensor_service.
        farm_context: Optional farm profile dictionary from services.farm_service.
        intel: Optional FarmIntelligenceResult from services.farm_intelligence.
        vision_result: Optional VisionAnalysisResult from services.vision_service.

    Returns:
        Structured WeatherFarmInsight.
    """
    ctx = farm_context or {}
    crop = (ctx.get("crop", "") or "").strip()
    crop_str = f"for {crop}" if crop else "for your crop"

    # 1. Telemetry Context
    is_online = getattr(reading, "is_online", True) if reading is not None else False
    soil_moisture = getattr(reading, "soil_moisture", None) if is_online else None
    sensor_temp = getattr(reading, "temperature", None) if is_online else None
    sensor_humidity = getattr(reading, "humidity", None) if is_online else None

    # 2. Meteorological Forecast Metrics
    effective_temp = max(weather.temperature, sensor_temp) if sensor_temp is not None else weather.temperature
    effective_humidity = max(weather.humidity, sensor_humidity) if sensor_humidity is not None else weather.humidity

    max_rain_prob = weather.precipitation_probability
    if weather.forecast_days:
        max_rain_prob = max(
            weather.precipitation_probability,
            max((d.precipitation_probability for d in weather.forecast_days[:2]), default=0),
        )

    total_rain_mm = weather.precipitation_amount_mm
    if weather.forecast_days:
        total_rain_mm += sum(d.precipitation_amount_mm for d in weather.forecast_days[:2])

    risks: list[WeatherRiskSignal] = []
    reasons: list[str] = []

    # =========================================================================
    # Step A: Heat & Water Stress Analysis
    # =========================================================================
    heat_risk_level = "Low"
    water_risk_level = "Low"

    if effective_temp >= 38.0:
        heat_risk_level = "High"
        risks.append(
            WeatherRiskSignal(
                category="heat_stress",
                severity="alert",
                title="Extreme Heat Stress",
                explanation=f"Temperatures reaching {effective_temp:.0f}°C cause rapid transpiration and pollen damage.",
                action="Apply irrigation during early morning or late evening hours to protect roots from overheating.",
            )
        )
        reasons.append("Extreme ambient temperature threshold exceeded.")
    elif effective_temp >= 34.0:
        heat_risk_level = "Elevated"
        risks.append(
            WeatherRiskSignal(
                category="heat_stress",
                severity="warning",
                title="Elevated Heat Stress",
                explanation=f"Warm conditions ({effective_temp:.0f}°C) increase canopy evaporation rate.",
                action="Monitor foliage for midday wilting and avoid midday spray applications.",
            )
        )
        reasons.append("Warm temperatures increasing evapotranspiration.")
    elif effective_temp >= 30.0:
        heat_risk_level = "Moderate"

    if soil_moisture is not None and soil_moisture < 30.0:
        water_risk_level = "High" if heat_risk_level in ("Elevated", "High") else "Moderate"
    elif soil_moisture is not None and soil_moisture < 20.0:
        water_risk_level = "High"

    # =========================================================================
    # Step B: Rain & Waterlogging Analysis
    # =========================================================================
    rain_risk_level = "Low"
    if total_rain_mm >= 25.0 or (weather.precipitation_amount_mm >= 15.0 and max_rain_prob >= 70):
        rain_risk_level = "High"
        risks.append(
            WeatherRiskSignal(
                category="excess_rain",
                severity="warning",
                title="Heavy Rain & Waterlogging Watch",
                explanation=f"Substantial rainfall (~{total_rain_mm:.0f}mm) is forecasted over the next 48 hours.",
                action="Ensure field drainage channels are cleared to prevent root zone saturation.",
            )
        )
        reasons.append("Heavy rainfall forecasted.")
    elif max_rain_prob >= 60 or total_rain_mm >= 10.0:
        rain_risk_level = "Moderate"

    # =========================================================================
    # Step C: Humidity & Foliar Disease Watch
    # =========================================================================
    foliar_risk_level = "Low"
    if effective_humidity >= 75.0 and 18.0 <= effective_temp <= 35.0:
        foliar_risk_level = "Watch" if max_rain_prob < 50 else "Elevated"

        action_note = "Ensure canopy ventilation, avoid overhead sprinkler wetting, and monitor leaves for spotting or blight."
        if vision_result is not None and getattr(vision_result, "success", False) and not getattr(vision_result, "healthy", True):
            action_note = (
                f"Recent leaf scan noted symptoms ({vision_result.diagnosis}). Warm, humid weather accelerates "
                "spore spread; monitor affected plants closely and isolate if needed."
            )

        risks.append(
            WeatherRiskSignal(
                category="humidity_disease",
                severity="warning",
                title="Foliar Disease Favorable Conditions",
                explanation="High relative humidity and warm air favor fungal spore germination and leaf wetness.",
                action=action_note,
            )
        )
        reasons.append("Atmospheric humidity and temperature favorable for foliar pathogens.")
    elif effective_humidity >= 65.0:
        foliar_risk_level = "Moderate"

    # =========================================================================
    # Step D: Wind & Spraying Conditions
    # =========================================================================
    wind_risk_level = "Normal"
    if weather.wind_speed_kmh >= 30.0:
        wind_risk_level = "Strong Wind"
        risks.append(
            WeatherRiskSignal(
                category="strong_wind",
                severity="warning",
                title="Strong Wind Advisory",
                explanation=f"Wind speed ({weather.wind_speed_kmh:.0f} km/h) disrupts uniform irrigation and causes spray drift.",
                action="Postpone foliar applications and overhead sprinkler irrigation until wind subsides.",
            )
        )
        reasons.append("Elevated wind speed disrupting field spraying.")
    elif weather.wind_speed_kmh >= 22.0:
        wind_risk_level = "Caution for Spraying"
        risks.append(
            WeatherRiskSignal(
                category="strong_wind",
                severity="info",
                title="Breezy Spraying Caution",
                explanation=f"Moderate breeze ({weather.wind_speed_kmh:.0f} km/h) can cause light droplet drift.",
                action="Exercise caution during foliar spray operations.",
            )
        )

    # =========================================================================
    # Step E: Weather-Informed Irrigation & Primary Action Synthesis
    # =========================================================================
    if soil_moisture is not None and soil_moisture < 30.0:
        if max_rain_prob >= 60:
            # Case B: Soil moisture low, but rain is imminent
            irrigation_label = "WAIT / DELAY"
            irrigation_detail = (
                f"Soil moisture is low ({soil_moisture:.0f}%), but rain is likely soon ({max_rain_prob}% probability). "
                "Hold off on irrigation and recheck soil moisture after the rain."
            )
            action_headline = "⏳ Wait before irrigating"
            action_detail = (
                f"Significant rainfall is forecasted soon ({max_rain_prob}% chance). "
                "Allow natural rain to replenish topsoil before turning on irrigation pumps."
            )
            primary_msg = f"Soil moisture is dry, but upcoming rain ({max_rain_prob}% chance) may provide sufficient natural water."
            overall_status = "WATCH"
            overall_sev = "warning"
        else:
            # Case A: Soil moisture low and no rain expected
            irrigation_label = "WATER SOON"
            irrigation_detail = (
                f"Soil moisture is low ({soil_moisture:.0f}%) and rain is unlikely ({max_rain_prob}% probability). "
                f"Irrigation is recommended {crop_str}."
            )
            action_headline = "💧 Water your crop"
            action_detail = (
                f"Soil moisture is below optimal ({soil_moisture:.0f}%) and little to no rain is expected in the forecast. "
                "Irrigate to protect root health."
            )
            primary_msg = f"Dry field conditions with minimal rain forecasted. Irrigation is needed {crop_str}."
            overall_status = "ATTENTION"
            overall_sev = "alert" if heat_risk_level in ("Elevated", "High") else "warning"
    elif soil_moisture is not None and soil_moisture > 60.0:
        if rain_risk_level in ("Moderate", "High"):
            # Case C: Soil already wet and heavy rain forecasted
            irrigation_label = "AVOID WATERING"
            irrigation_detail = (
                f"Soil is already sufficiently wet ({soil_moisture:.0f}%) and rainfall is forecasted. "
                "Avoid unnecessary watering and monitor field drainage."
            )
            action_headline = "🌧 Avoid unnecessary irrigation"
            action_detail = (
                f"Soil moisture is high and further rainfall is anticipated (~{total_rain_mm:.0f}mm). "
                "Check drainage outlets to prevent waterlogging."
            )
            primary_msg = "Saturated soil combined with incoming rain creates waterlogging risk. Ensure good drainage."
            overall_status = "ATTENTION"
            overall_sev = "warning"
        else:
            irrigation_label = "NORMAL"
            irrigation_detail = f"Soil is sufficiently moist ({soil_moisture:.0f}%). No irrigation required."
            action_headline = "🌱 No watering needed right now"
            action_detail = f"Soil moisture ({soil_moisture:.0f}%) is healthy. Weather conditions remain stable."
            primary_msg = "Field moisture is in a safe range. Weather conditions are balanced."
            overall_status = "NORMAL"
            overall_sev = "good"
    else:
        # Moisture is between 30% and 60%, or sensor is offline
        if rain_risk_level == "High":
            irrigation_label = "AVOID WATERING"
            irrigation_detail = f"Heavy rainfall forecasted ({total_rain_mm:.0f}mm). Keep drainage clear."
            action_headline = "🌧 Prepare field drainage"
            action_detail = "Heavy rain is on the horizon. Inspect drainage paths and avoid running irrigation."
            primary_msg = "Substantial precipitation expected. Maintain open drainage to avoid standing water."
            overall_status = "ATTENTION"
            overall_sev = "warning"
        elif heat_risk_level in ("Elevated", "High"):
            # Case D: High Heat
            irrigation_label = "NORMAL"
            irrigation_detail = f"Ambient heat ({effective_temp:.0f}°C) is elevated. Maintain regular soil monitoring."
            action_headline = "🌡️ Monitor soil in hot weather"
            action_detail = f"Elevated temperatures ({effective_temp:.0f}°C) will dry out soil faster. Irrigate during cool morning hours if soil dips."
            primary_msg = f"Hot weather is increasing evapotranspiration {crop_str}. Monitor field soil moisture closely."
            overall_status = "ATTENTION"
            overall_sev = "warning"
        elif foliar_risk_level in ("Watch", "Elevated"):
            # Case E: High Humidity / Disease
            irrigation_label = "NORMAL"
            irrigation_detail = "High atmospheric moisture. Avoid unnecessary overhead wetting."
            action_headline = "🌿 Monitor crop foliage"
            action_detail = "Warm and humid conditions favor foliar fungal development. Inspect crop leaves for spots or discoloration."
            primary_msg = f"High humidity ({effective_humidity:.0f}%) creates conditions favorable for foliar fungal spread."
            overall_status = "WATCH"
            overall_sev = "warning"
        elif wind_risk_level == "Strong Wind":
            # Case F: Strong Wind
            irrigation_label = "NORMAL"
            irrigation_detail = f"Wind ({weather.wind_speed_kmh:.0f} km/h) causes spray drift. Postpone spraying."
            action_headline = "💨 Postpone foliar spraying"
            action_detail = f"Strong wind ({weather.wind_speed_kmh:.0f} km/h) will disperse droplets. Wait for calmer air."
            primary_msg = f"Gusty wind ({weather.wind_speed_kmh:.0f} km/h) makes spraying and sprinkler irrigation inefficient."
            overall_status = "WATCH"
            overall_sev = "warning"
        else:
            irrigation_label = "NORMAL"
            irrigation_detail = "Weather conditions are balanced. Maintain routine scheduled watering."
            action_headline = "🌱 Conditions favorable"
            action_detail = f"Weather and temperature ({weather.temperature:.0f}°C) are favorable {crop_str}. Continue regular care."
            primary_msg = f"Favorable weather conditions with moderate temperatures and balanced humidity {crop_str}."
            overall_status = "NORMAL"
            overall_sev = "good"

    return WeatherFarmInsight(
        overall_status=overall_status,
        severity=overall_sev,
        primary_message=primary_msg,
        farmer_action_headline=action_headline,
        farmer_action_detail=action_detail,
        irrigation_impact_label=irrigation_label,
        irrigation_impact_detail=irrigation_detail,
        heat_stress_risk=heat_risk_level,
        water_stress_risk=water_risk_level,
        excess_rain_risk=rain_risk_level,
        humidity_disease_risk=foliar_risk_level,
        wind_risk=wind_risk_level,
        risks=risks,
        reasons=reasons,
        confidence="high",
        forecast_window="Next 24–48 Hours",
    )
