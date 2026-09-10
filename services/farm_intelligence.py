"""Smart Farm Intelligence and Decision Engine for KisanSense.

Evaluates multi-sensor telemetry, farm profile context, and hardware health
to produce deterministic, explainable, farmer-friendly agricultural recommendations.
Acts as the authoritative intelligence layer consumed by the Home dashboard and Chatbot.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from services.hardware_client import FAULT_STATUSES
from services.irrigation_service import IrrigationStatus, get_irrigation_status
from services.sensor_service import SensorReading

# Physical sanity limits for agricultural telemetry
MOISTURE_MIN_VALID = 0.0
MOISTURE_MAX_VALID = 100.0
TEMP_MIN_VALID = -10.0
TEMP_MAX_VALID = 65.0
HUMIDITY_MIN_VALID = 0.0
HUMIDITY_MAX_VALID = 100.0

# Staleness threshold in seconds for telemetry (5 minutes)
STALE_THRESHOLD_SECONDS = 300

# Severity ranking for deterministic sorting
SEVERITY_WEIGHTS: dict[str, int] = {
    "critical": 50,
    "alert": 40,
    "warning": 30,
    "good": 20,
    "info": 10,
}

# Category weights to break ties in favor of compound or safety alerts
CATEGORY_WEIGHTS: dict[str, int] = {
    "hardware_safety": 50,
    "compound_risk": 40,
    "water_stress": 30,
    "foliar_health": 25,
    "heat_stress": 20,
    "humidity_risk": 10,
}


@dataclass
class FarmCondition:
    """Represents a discrete evaluated condition or risk on the farm."""

    category: str  # "water_stress" | "heat_stress" | "humidity_risk" | "compound_risk" | "hardware_safety"
    code: str  # Machine-readable identifier
    severity: str  # "critical" | "alert" | "warning" | "good" | "info"
    title: str  # Farmer-facing headline
    explanation: str  # Why it matters / agronomic observation
    recommended_action: str  # Actionable advice
    confidence: str = "high"  # "high" | "moderate" | "low"


@dataclass
class FarmIntelligenceResult:
    """Authoritative structured output of the farm decision engine."""

    primary_status: str  # e.g. "Optimal Conditions", "Attention Needed", "Action Required", "Sensor Offline"
    primary_severity: str  # "good" | "warning" | "alert" | "critical"
    overall_summary: str  # Concise 1-2 sentence overview for dashboard & chatbot
    conditions: list[FarmCondition] = field(default_factory=list)
    irrigation_status: IrrigationStatus | None = None
    data_quality: str = "reliable"  # "reliable" | "degraded" | "stale" | "offline" | "fault" | "invalid"
    data_quality_reasons: list[str] = field(default_factory=list)
    timestamp: str = ""


def _validate_telemetry_quality(reading: SensorReading) -> tuple[str, list[str]]:
    """Enforce Safety Gate: Check whether telemetry is trustworthy before agronomic reasoning."""
    reasons: list[str] = []

    # 1. Explicit Hardware Fault Check (takes precedence over generic connectivity)
    raw_status = (getattr(reading, "raw_status", "ok") or "ok").strip().lower()
    if raw_status in FAULT_STATUSES:
        reasons.append(f"Hardware reporting explicit sensor fault: {raw_status}.")
        return "fault", reasons

    # 2. Connectivity check
    if not reading.is_online:
        reasons.append("Sensor probe is offline or disconnected.")
        return "offline", reasons

    if raw_status in ("stale_or_offline", "no_signal"):
        reasons.append("Hardware signal missing or communication timed out.")
        return "stale", reasons

    # 3. Physical Sanity Bounds Check
    sm = reading.soil_moisture
    t = reading.temperature
    h = reading.humidity

    if not (MOISTURE_MIN_VALID <= sm <= MOISTURE_MAX_VALID):
        reasons.append(f"Soil moisture {sm}% out of physical bounds [{MOISTURE_MIN_VALID}, {MOISTURE_MAX_VALID}].")
        return "invalid", reasons

    if not (TEMP_MIN_VALID <= t <= TEMP_MAX_VALID):
        reasons.append(f"Temperature {t}°C out of physical bounds [{TEMP_MIN_VALID}, {TEMP_MAX_VALID}].")
        return "invalid", reasons

    if not (HUMIDITY_MIN_VALID <= h <= HUMIDITY_MAX_VALID):
        reasons.append(f"Humidity {h}% out of physical bounds [{HUMIDITY_MIN_VALID}, {HUMIDITY_MAX_VALID}].")
        return "invalid", reasons

    # 4. Battery Advisory Check (non-fatal, but noted)
    batt = getattr(reading, "battery_voltage", None)
    if batt is not None and batt < 3.4:
        reasons.append(f"Hardware battery low ({batt:.2f}V).")

    return "reliable", reasons


def _calculate_confidence(
    data_quality: str,
    farm_context: dict[str, Any] | None = None,
    is_compound: bool = False,
) -> str:
    """Deterministically assign confidence based on telemetry quality and profile completeness."""
    if data_quality != "reliable":
        return "low"

    ctx = farm_context or {}
    has_crop = bool(ctx.get("crop", "").strip())
    has_stage = bool(ctx.get("growth_stage", "").strip())

    if is_compound:
        return "high" if has_crop and has_stage else "moderate"

    return "high" if has_crop else "moderate"


def _analyze_water_stress(
    soil_moisture: float,
    farm_context: dict[str, Any] | None = None,
    confidence: str = "high",
) -> FarmCondition:
    """Analyze soil moisture levels and water stress."""
    ctx = farm_context or {}
    crop = ctx.get("crop", "").strip()
    stage = ctx.get("growth_stage", "").strip()
    soil_type = ctx.get("soil_type", "").strip()

    crop_phrase = f"for your {crop}" if crop else "for crop growth"
    is_sensitive_stage = stage in ("Flowering", "Fruiting / Pod Formation")

    # Boundary: < 20% -> Severe dryness
    if soil_moisture < 20.0:
        severity = "critical" if is_sensitive_stage else "alert"
        stage_note = f" Moisture stress is especially critical during the {stage} stage." if stage else ""
        soil_note = f" In {soil_type}, moisture depletion occurs rapidly." if soil_type == "Sandy Soil" else ""
        return FarmCondition(
            category="water_stress",
            code="SEVERE_DRYNESS",
            severity=severity,
            title="Severe Soil Dryness",
            explanation=f"Soil moisture is critically low at {soil_moisture:.0f}% {crop_phrase}.{stage_note}{soil_note}",
            recommended_action="Irrigate promptly to prevent plant water stress and preserve yield potential.",
            confidence=confidence,
        )

    # Boundary: 20% to < 30% -> Moderate dryness
    if soil_moisture < 30.0:
        stage_note = f" Consistent moisture is recommended during {stage}." if stage else ""
        return FarmCondition(
            category="water_stress",
            code="MODERATE_DRYNESS",
            severity="alert",
            title="Low Soil Moisture",
            explanation=f"Soil moisture ({soil_moisture:.0f}%) has fallen below the 30% healthy threshold {crop_phrase}.{stage_note}",
            recommended_action="Consider irrigating soon to restore optimal soil moisture levels.",
            confidence=confidence,
        )

    # Boundary: 30% to 60% -> Adequate moisture
    if soil_moisture <= 60.0:
        return FarmCondition(
            category="water_stress",
            code="ADEQUATE_MOISTURE",
            severity="good",
            title="Adequate Soil Moisture",
            explanation=f"Soil moisture ({soil_moisture:.0f}%) is within the healthy 30%–60% range {crop_phrase}.",
            recommended_action="No irrigation needed at this time. Maintain regular monitoring.",
            confidence=confidence,
        )

    # Boundary: > 60% to 75% -> Excessive moisture
    if soil_moisture <= 75.0:
        soil_note = f" High retention in {soil_type} may slow drying." if soil_type in ("Clay Soil", "Black / Regur Soil") else ""
        return FarmCondition(
            category="water_stress",
            code="EXCESSIVE_MOISTURE",
            severity="warning",
            title="Elevated Soil Moisture",
            explanation=f"Soil moisture is high at {soil_moisture:.0f}%. Soil is moist and does not require additional water.{soil_note}",
            recommended_action="Withhold irrigation to allow soil aeration and healthy root respiration.",
            confidence=confidence,
        )

    # Boundary: > 75% -> Waterlogging risk
    severity = "alert" if soil_type in ("Clay Soil", "Black / Regur Soil") else "warning"
    return FarmCondition(
        category="water_stress",
        code="WATERLOGGING_RISK",
        severity=severity,
        title="High Moisture / Waterlogging Risk",
        explanation=f"Soil moisture is very high at {soil_moisture:.0f}%. Saturated soil can restrict root oxygen.",
        recommended_action="Ensure field drainage channels are clear and halt all automated watering.",
        confidence=confidence,
    )


def _analyze_heat_stress(
    temperature: float,
    farm_context: dict[str, Any] | None = None,
    confidence: str = "high",
) -> FarmCondition:
    """Analyze ambient temperature and heat burden."""
    ctx = farm_context or {}
    crop = ctx.get("crop", "").strip()
    crop_target = f"for {crop}" if crop else "for most crops"

    # Boundary: 15°C to 35°C -> Normal range
    if 15.0 <= temperature <= 35.0:
        return FarmCondition(
            category="heat_stress",
            code="TEMP_NORMAL",
            severity="good",
            title="Optimal Temperature",
            explanation=f"Field temperature ({temperature:.0f}°C) is within comfortable range (15°C–35°C) {crop_target}.",
            recommended_action="Thermal conditions are favorable for steady growth.",
            confidence=confidence,
        )

    # Boundary: < 15°C -> Cool
    if temperature < 15.0:
        return FarmCondition(
            category="heat_stress",
            code="TEMP_COOL",
            severity="info",
            title="Cool Temperature",
            explanation=f"Field temperature ({temperature:.0f}°C) is on the lower side for tropical crop growth.",
            recommended_action="Monitor plant growth rates; growth may be slower during cooler periods.",
            confidence=confidence,
        )

    # Boundary: > 35°C to 40°C -> Elevated heat
    if temperature <= 40.0:
        return FarmCondition(
            category="heat_stress",
            code="ELEVATED_HEAT",
            severity="warning",
            title="Elevated Temperature",
            explanation=f"Field temperature ({temperature:.0f}°C) is higher than normal. Increased crop transpiration is likely.",
            recommended_action="Monitor canopy for wilting and avoid midday chemical spraying.",
            confidence=confidence,
        )

    # Boundary: > 40°C -> High/Severe heat-risk condition
    return FarmCondition(
        category="heat_stress",
        code="SEVERE_HEAT_RISK",
        severity="alert",
        title="High Heat-Stress Risk",
        explanation=f"Field temperature ({temperature:.0f}°C) indicates severe heat conditions. High thermal stress on vegetation.",
        recommended_action="Protect sensitive crops where feasible and consider irrigating during cooler morning or evening hours.",
        confidence=confidence,
    )


def _analyze_humidity_risk(
    humidity: float,
    farm_context: dict[str, Any] | None = None,
    confidence: str = "high",
) -> FarmCondition:
    """Analyze ambient canopy humidity."""
    # Boundary: 40% to 75% -> Normal range
    if 40.0 <= humidity <= 75.0:
        return FarmCondition(
            category="humidity_risk",
            code="HUMIDITY_NORMAL",
            severity="good",
            title="Normal Humidity",
            explanation=f"Air humidity ({humidity:.0f}%) is within a balanced range (40%–75%).",
            recommended_action="Canopy atmospheric moisture is balanced.",
            confidence=confidence,
        )

    # Boundary: < 35% -> Dry air
    if humidity < 35.0:
        return FarmCondition(
            category="humidity_risk",
            code="DRY_AIR",
            severity="info",
            title="Dry Atmospheric Conditions",
            explanation=f"Ambient relative humidity is low ({humidity:.0f}%). Dry air increases moisture loss from foliage.",
            recommended_action="Observe topsoil and crop leaves for signs of quick moisture depletion.",
            confidence=confidence,
        )

    # Boundary: > 80% -> High humidity
    if humidity > 80.0:
        return FarmCondition(
            category="humidity_risk",
            code="HIGH_HUMIDITY",
            severity="warning",
            title="High Canopy Humidity",
            explanation=f"Ambient air humidity is high ({humidity:.0f}%). High humidity combined with warm air may favor fungal disease development.",
            recommended_action="Inspect foliage for signs of mildew or leaf spot, and maintain good field airflow.",
            confidence=confidence,
        )

    # Intermediate zones (35-40% or 75-80%)
    return FarmCondition(
        category="humidity_risk",
        code="HUMIDITY_ACCEPTABLE",
        severity="good",
        title="Acceptable Humidity",
        explanation=f"Air humidity ({humidity:.0f}%) is at an acceptable level.",
        recommended_action="No humidity-related action necessary.",
        confidence=confidence,
    )


def _analyze_compound_conditions(
    soil_moisture: float,
    temperature: float,
    humidity: float,
    farm_context: dict[str, Any] | None = None,
    confidence: str = "moderate",
) -> list[FarmCondition]:
    """Detect compound multi-sensor interactions."""
    compounds: list[FarmCondition] = []
    ctx = farm_context or {}
    stage = ctx.get("growth_stage", "").strip()

    # Compound 1: Low Soil Moisture (<30%) + High Temperature (>35°C)
    if soil_moisture < 30.0 and temperature > 35.0:
        is_severe = soil_moisture < 20.0 or temperature > 40.0 or stage in ("Flowering", "Fruiting / Pod Formation")
        severity = "critical" if is_severe else "alert"
        compounds.append(
            FarmCondition(
                category="compound_risk",
                code="COMPOUND_HEAT_DROUGHT",
                severity=severity,
                title="Compound Heat & Water Stress",
                explanation=(
                    f"Combined elevated temperature ({temperature:.0f}°C) and low soil moisture ({soil_moisture:.0f}%) "
                    f"indicate increased crop water-stress risk."
                ),
                recommended_action="Prioritize irrigation during cooler morning or evening hours to reduce acute moisture stress.",
                confidence=confidence,
            )
        )

    # Compound 2: High Soil Moisture (>60%) + High Humidity (>80%)
    if soil_moisture > 60.0 and humidity > 80.0:
        compounds.append(
            FarmCondition(
                category="compound_risk",
                code="COMPOUND_WET_HUMID",
                severity="warning",
                title="Wet Soil & High Humidity Environment",
                explanation=(
                    f"Wet soil ({soil_moisture:.0f}%) combined with high canopy humidity ({humidity:.0f}%) creates "
                    f"conditions that may favor fungal disease development and slow root aeration."
                ),
                recommended_action="Withhold irrigation, ensure field drainage, and inspect crop foliage for fungal symptoms.",
                confidence=confidence,
            )
        )

    # Compound 3: High Temperature (>35°C) + High Humidity (>70%)
    if temperature > 35.0 and humidity > 70.0:
        compounds.append(
            FarmCondition(
                category="compound_risk",
                code="COMPOUND_HEAT_HUMID",
                severity="warning",
                title="High Heat & Stagnant Humidity",
                explanation=(
                    f"Elevated temperature ({temperature:.0f}°C) paired with high humidity ({humidity:.0f}%) creates a "
                    f"high heat-index burden and reduces natural evaporative cooling for crops."
                ),
                recommended_action="Monitor plant vigor closely during peak daytime heat.",
                confidence=confidence,
            )
        )

    return compounds


def evaluate_farm_intelligence(
    reading: SensorReading,
    farm_context: dict[str, Any] | None = None,
    vision_result: Any | None = None,
    weather_context: Any | None = None,
) -> FarmIntelligenceResult:
    """Evaluate farm conditions and generate an explainable intelligence assessment.

    Args:
        reading: Current SensorReading contract (from Simulator or Hardware).
        farm_context: Optional farm profile dict from services.farm_service.
        vision_result: Optional VisionAnalysisResult contract from services.vision_service.
        weather_context: Optional WeatherSnapshot or dict from services.weather_service.

    Returns:
        Structured FarmIntelligenceResult.
    """
    ctx = farm_context or {}
    now_str = datetime.now().strftime("%H:%M:%S")

    # =========================================================================
    # 1. SAFETY GATE: Validate Telemetry Quality
    # =========================================================================
    quality, quality_reasons = _validate_telemetry_quality(reading)

    # Fetch authoritative irrigation decision
    base_irrigation = get_irrigation_status(
        soil_moisture=reading.soil_moisture,
        farm_context=ctx,
        is_online=reading.is_online,
        raw_status=getattr(reading, "raw_status", "ok"),
        weather_context=weather_context,
    )

    # If telemetry is unsafe, offline, or invalid, FAIL SAFE IMMEDIATELY
    if quality != "reliable":
        reasons_summary = " ".join(quality_reasons)

        # Enforce irrigation fail-safe on untrustworthy data
        safe_irrigation = IrrigationStatus(
            needs_water=False,
            label=base_irrigation.label if not base_irrigation.needs_water else "Sensor Offline",
            detail=base_irrigation.detail if not base_irrigation.needs_water else "Telemetry is untrustworthy or stale. Please verify sensor before irrigating.",
            status_type="warning",
        )

        if quality == "offline":
            primary_status = "Sensor Offline"
            overall_summary = (
                "Field sensor telemetry is currently unavailable. Automated recommendations are suspended. "
                "Please inspect field sensor power, probe connection, and network reception."
            )
            cond = FarmCondition(
                category="hardware_safety",
                code="SENSOR_OFFLINE",
                severity="alert",
                title="Sensor Offline",
                explanation="No real-time signal received from field probe.",
                recommended_action="Inspect field device wiring, battery, and physical probe connection.",
                confidence="high",
            )
        elif quality == "fault":
            primary_status = "Hardware Fault Detected"
            overall_summary = (
                f"Field hardware reported an explicit sensor issue ({reasons_summary}). "
                "Automated irrigation advice is blocked for crop safety."
            )
            cond = FarmCondition(
                category="hardware_safety",
                code="HARDWARE_FAULT",
                severity="critical" if "probe_disconnected" in reasons_summary else "alert",
                title="Hardware Sensor Fault",
                explanation=reasons_summary,
                recommended_action="Check physical soil moisture probe wiring and verify sensor calibration.",
                confidence="high",
            )
        elif quality == "invalid":
            primary_status = "Invalid Telemetry"
            overall_summary = (
                f"Received telemetry values are physically invalid ({reasons_summary}). "
                "Calculations suspended to prevent erroneous watering."
            )
            cond = FarmCondition(
                category="hardware_safety",
                code="INVALID_DATA",
                severity="alert",
                title="Invalid Sensor Readings",
                explanation=reasons_summary,
                recommended_action="Recalibrate or reboot field sensor hardware.",
                confidence="low",
            )
        else:  # stale
            primary_status = "Stale Telemetry"
            overall_summary = (
                "Sensor telemetry has not refreshed recently. Readings may not reflect current field moisture."
            )
            cond = FarmCondition(
                category="hardware_safety",
                code="STALE_DATA",
                severity="warning",
                title="Stale Sensor Data",
                explanation="Sensor telemetry is older than the acceptable refresh interval.",
                recommended_action="Verify field node power and network connectivity before taking action.",
                confidence="low",
            )

        fail_safe_conditions = [cond]
        # If a valid vision screening result exists, append as an advisory foliar condition
        # while keeping sensor safety and irrigation fail-safe authoritative
        if vision_result is not None and getattr(vision_result, "success", False) and not getattr(vision_result, "healthy", True):
            fail_safe_conditions.append(
                FarmCondition(
                    category="foliar_health",
                    code=vision_result.disease_code,
                    severity="warning",
                    title=f"Advisory: {vision_result.diagnosis}",
                    explanation=(
                        f"Visual screening noted possible leaf symptoms ({vision_result.diagnosis}). "
                        "Field sensors are offline or untrustworthy, so automated environmental validation is suspended. "
                        "Inspect foliage physically."
                    ),
                    recommended_action=vision_result.recommended_action,
                    confidence=vision_result.confidence_level,
                )
            )

        return FarmIntelligenceResult(
            primary_status=primary_status,
            primary_severity=cond.severity,
            overall_summary=overall_summary,
            conditions=fail_safe_conditions,
            irrigation_status=safe_irrigation,
            data_quality=quality,
            data_quality_reasons=quality_reasons,
            timestamp=now_str,
        )

    # =========================================================================
    # 2. AGRONOMIC SUBSYSTEM REASONING (Telemetry is reliable)
    # =========================================================================
    conf_direct = _calculate_confidence(quality, ctx, is_compound=False)
    conf_compound = _calculate_confidence(quality, ctx, is_compound=True)

    c_water = _analyze_water_stress(reading.soil_moisture, ctx, confidence=conf_direct)
    c_heat = _analyze_heat_stress(reading.temperature, ctx, confidence=conf_direct)
    c_humidity = _analyze_humidity_risk(reading.humidity, ctx, confidence=conf_direct)
    compounds = _analyze_compound_conditions(
        reading.soil_moisture, reading.temperature, reading.humidity, ctx, confidence=conf_compound
    )

    all_conditions = [c_water, c_heat, c_humidity] + compounds

    # Add hardware low battery warning if detected
    batt = getattr(reading, "battery_voltage", None)
    if batt is not None and batt < 3.4:
        all_conditions.append(
            FarmCondition(
                category="hardware_safety",
                code="BATTERY_LOW",
                severity="warning",
                title="Node Battery Low",
                explanation=f"Field sensor node battery is at {batt:.2f}V (threshold 3.40V).",
                recommended_action="Recharge solar battery unit to avoid transmission interruptions.",
                confidence="high",
            )
        )

    # Add plant vision screening condition and compound foliar risk if present
    if vision_result is not None and getattr(vision_result, "success", False):
        if not getattr(vision_result, "healthy", True):
            urgency = getattr(vision_result, "treatment_urgency", "moderate")
            foliar_sev = "alert" if urgency == "immediate" else "warning"
            all_conditions.append(
                FarmCondition(
                    category="foliar_health",
                    code=vision_result.disease_code,
                    severity=foliar_sev,
                    title=f"Foliar Health: {vision_result.diagnosis}",
                    explanation=vision_result.explanation,
                    recommended_action=vision_result.recommended_action,
                    confidence=vision_result.confidence_level,
                )
            )

            # Compound foliar risk A: Elevated humidity + foliar pathogen
            if reading.humidity > 75.0 and (
                getattr(vision_result, "category", "") == "fungal"
                or "blight" in vision_result.disease_code.lower()
                or "spot" in vision_result.disease_code.lower()
            ):
                all_conditions.append(
                    FarmCondition(
                        category="compound_risk",
                        code="COMPOUND_FUNGAL_HUMIDITY",
                        severity="alert",
                        title="Elevated Foliar Disease Risk",
                        explanation=(
                            f"High canopy humidity ({reading.humidity:.0f}%) may favor further foliar disease development "
                            f"consistent with {vision_result.diagnosis}."
                        ),
                        recommended_action=(
                            "Inspect affected plants physically, improve canopy ventilation, and avoid unnecessary overhead watering."
                        ),
                        confidence="high",
                    )
                )

            # Compound foliar risk B: Low soil moisture + chlorosis
            if reading.soil_moisture < 30.0 and (
                vision_result.disease_code == "NUTRIENT_CHLOROSIS"
                or getattr(vision_result, "category", "") == "abiotic_stress"
            ):
                all_conditions.append(
                    FarmCondition(
                        category="compound_risk",
                        code="COMPOUND_DRY_CHLOROSIS",
                        severity="warning",
                        title="Foliar Yellowing with Soil Moisture Deficit",
                        explanation=(
                            f"Leaf yellowing is present along with low soil moisture ({reading.soil_moisture:.0f}%). "
                            "Visual signs are consistent with moisture or nutrient stress."
                        ),
                        recommended_action=(
                            "Check root-zone moisture before deciding on fertilizer or corrective treatments."
                        ),
                        confidence="moderate",
                    )
                )

            # Compound foliar risk C: Saturated soil + chlorosis
            if reading.soil_moisture > 70.0 and (
                vision_result.disease_code == "NUTRIENT_CHLOROSIS"
                or getattr(vision_result, "category", "") == "abiotic_stress"
            ):
                all_conditions.append(
                    FarmCondition(
                        category="compound_risk",
                        code="COMPOUND_WET_CHLOROSIS",
                        severity="warning",
                        title="Foliar Yellowing with Saturated Soil",
                        explanation=(
                            f"Leaf yellowing is present with high soil moisture ({reading.soil_moisture:.0f}%). "
                            "Excess moisture could indicate root stress or waterlogging."
                        ),
                        recommended_action=(
                            "Do not add irrigation; inspect field drainage channels."
                        ),
                        confidence="moderate",
                    )
                )
        else:
            all_conditions.append(
                FarmCondition(
                    category="foliar_health",
                    code="HEALTHY_FOLIAGE",
                    severity="good",
                    title=f"Foliar Health: {vision_result.diagnosis}",
                    explanation=vision_result.explanation,
                    recommended_action=vision_result.recommended_action,
                    confidence=vision_result.confidence_level,
                )
            )

    # Sort conditions deterministically by severity weight, then category weight
    all_conditions.sort(
        key=lambda c: (
            SEVERITY_WEIGHTS.get(c.severity, 0),
            CATEGORY_WEIGHTS.get(c.category, 0),
        ),
        reverse=True,
    )

    # =========================================================================
    # 3. SYNTHESIZE PRIMARY STATUS & OVERALL SUMMARY
    # =========================================================================
    top_condition = all_conditions[0]
    top_severity = top_condition.severity

    crop = ctx.get("crop", "").strip()
    crop_name = f"for your {crop}" if crop else "for your field"

    if top_severity == "critical":
        primary_status = "Action Required"
        overall_summary = (
            f"Urgent attention needed {crop_name}: {top_condition.explanation} {top_condition.recommended_action}"
        )
    elif top_severity == "alert":
        primary_status = "Action Recommended"
        overall_summary = (
            f"Action advised {crop_name}: {top_condition.explanation} {top_condition.recommended_action}"
        )
    elif top_severity == "warning":
        primary_status = "Attention Needed"
        overall_summary = (
            f"Attention suggested {crop_name}: {top_condition.explanation} {top_condition.recommended_action}"
        )
    else:
        primary_status = "Optimal Conditions"
        overall_summary = (
            f"Field conditions are currently optimal {crop_name}. Soil moisture and climate are balanced."
        )

    return FarmIntelligenceResult(
        primary_status=primary_status,
        primary_severity=top_severity,
        overall_summary=overall_summary,
        conditions=all_conditions,
        irrigation_status=base_irrigation,
        data_quality=quality,
        data_quality_reasons=quality_reasons,
        timestamp=now_str,
    )
