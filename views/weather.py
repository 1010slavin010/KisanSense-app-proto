"""Weather & Climate Intelligence page for KisanSense.

Connects agrarian weather forecasts with farm profile context, live sensor
telemetry, Smart Farm Intelligence, irrigation logic, and crop vision screening.
Operates with a deterministic agrarian simulation engine (100% offline).
Clearly marks simulated weather data.
"""

from __future__ import annotations

import streamlit as st

from components.breadcrumbs import render_breadcrumbs
from services.farm_intelligence import evaluate_farm_intelligence
from services.farm_service import get_farm_profile, is_profile_configured
from services.sensor_service import get_current_sensor_data
from services.weather_intelligence import evaluate_weather_intelligence
from services.weather_service import get_weather_snapshot
from utils.translations import t


def _go_to_assistant(prompt: str = "") -> None:
    st.session_state.page = "assistant"
    if prompt:
        st.session_state["preset_assistant_prompt"] = prompt


def render() -> None:
    # ---------------------------------------------------------
    # 1. Fetch Context & Telemetry
    # ---------------------------------------------------------
    profile = get_farm_profile()
    farm_ctx = profile.to_dict()
    has_profile = is_profile_configured(profile)

    location = profile.location.strip() if (profile and profile.location and profile.location.strip()) else "Mandya, Karnataka"
    crop_name = profile.crop.strip() if (profile and profile.crop and profile.crop.strip()) else "General Crop"

    sim_condition = st.session_state.get("sim_condition", "NORMAL")
    reading = get_current_sensor_data(condition=sim_condition)

    # Deterministic Agrarian Weather Snapshot
    weather = get_weather_snapshot(location=location, condition_hint=sim_condition)
    st.session_state.latest_weather_snapshot = weather

    # Farm Intelligence & Vision Context
    intel = evaluate_farm_intelligence(
        reading,
        farm_context=farm_ctx if has_profile else None,
        weather_context=weather,
    )
    vision_result = st.session_state.get("latest_vision_result", None)

    # Unified Weather Farm Insight
    insight = evaluate_weather_intelligence(weather, reading, farm_ctx, intel, vision_result)

    # ---------------------------------------------------------
    # 2. Header & Location Context
    # ---------------------------------------------------------
    render_breadcrumbs(t("weather_page_title"), "weather")

    st.markdown(
        f'<h1 class="ks-page-title hero-title">🌤️ {t("weather_page_title")}</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p class="hero-tagline">{t("weather_page_subtitle")}</p>',
        unsafe_allow_html=True,
    )

    badge_profile = f"📍 {location} · 🌾 {crop_name}"
    st.markdown(
        f"""
        <div class="weather-context-banner">
            <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 8px;">
                <span style="font-weight: 600; color: var(--color-text);">{badge_profile}</span>
                <span class="weather-badge-demo">⚙️ SIMULATED WEATHER ({sim_condition})</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---------------------------------------------------------
    # 3. Current Weather Metric Cards (5 Cards)
    # ---------------------------------------------------------
    st.markdown('<div class="insights-header">CURRENT WEATHER</div>', unsafe_allow_html=True)
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.markdown(
            f"""
            <div class="weather-metric-card">
                <div class="weather-metric-label">Temperature</div>
                <div class="weather-metric-value">{weather.temperature_c:.1f}°C</div>
                <div class="weather-metric-sub">{weather.condition}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        rain_prob = weather.rain_probability
        rain_mm = weather.precipitation_mm
        st.markdown(
            f"""
            <div class="weather-metric-card">
                <div class="weather-metric-label">Rain Probability</div>
                <div class="weather-metric-value">{rain_prob}%</div>
                <div class="weather-metric-sub">{rain_mm:.1f} mm expected</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col3:
        st.markdown(
            f"""
            <div class="weather-metric-card">
                <div class="weather-metric-label">Air Humidity</div>
                <div class="weather-metric-value">{weather.humidity:.0f}%</div>
                <div class="weather-metric-sub">Canopy microclimate</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col4:
        st.markdown(
            f"""
            <div class="weather-metric-card">
                <div class="weather-metric-label">Wind Speed</div>
                <div class="weather-metric-value">{weather.wind_speed_kmh:.1f} <span style="font-size: 0.85rem;">km/h</span></div>
                <div class="weather-metric-sub">{weather.wind_direction} breeze</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col5:
        st.markdown(
            f"""
            <div class="weather-metric-card">
                <div class="weather-metric-label">Evapotranspiration</div>
                <div class="weather-metric-value">{weather.evapotranspiration_mm:.1f} <span style="font-size: 0.85rem;">mm/d</span></div>
                <div class="weather-metric-sub">{weather.solar_irradiance_w_m2:.0f} W/m² solar</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 4. Immediate Action Hero: "FARM WEATHER ADVISORY"
    # ---------------------------------------------------------
    status_color_class = f"weather-action-{insight.status_type}"
    status_label = "CRITICAL ACTION" if insight.status_type == "alert" else ("ADVISORY" if insight.status_type == "warning" else "FAVORABLE")

    st.markdown(
        f"""
        <div class="weather-action-hero {status_color_class}">
            <div class="weather-action-badge">● FARM WEATHER ADVISORY — {status_label}</div>
            <div class="weather-action-headline">{insight.primary_action}</div>
            <div class="weather-action-detail">{insight.action_detail}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 5. Farm Impact Grid
    # ---------------------------------------------------------
    st.markdown(
        f'<div class="weather-section-title">🌾 Farm Impact Analysis</div>',
        unsafe_allow_html=True,
    )

    col_impact1, col_impact2 = st.columns(2)

    with col_impact1:
        st.markdown(
            f"""
            <div class="weather-impact-card">
                <div class="weather-impact-heading">🌱 {crop_name} Impact</div>
                <div class="weather-impact-body">{insight.crop_impact_summary}</div>
            </div>
            <div class="weather-impact-card" style="margin-top: 10px;">
                <div class="weather-impact-heading">💧 Irrigation Guidance</div>
                <div class="weather-impact-body">{insight.irrigation_guidance}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_impact2:
        st.markdown(
            f"""
            <div class="weather-impact-card">
                <div class="weather-impact-heading">🛡️ Crop Health & Pest Risk</div>
                <div class="weather-impact-body">{insight.crop_health_risk_summary}</div>
            </div>
            <div class="weather-impact-card" style="margin-top: 10px;">
                <div class="weather-impact-heading">🚜 Spraying & Field Operations</div>
                <div class="weather-impact-body">{insight.field_work_advisory}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 6. 3-Day Farm Forecast
    # ---------------------------------------------------------
    st.markdown(
        f'<div class="weather-section-title">📅 3-Day Agronomic Forecast</div>',
        unsafe_allow_html=True,
    )

    if weather.forecast:
        f_cols = st.columns(len(weather.forecast))
        for idx, day in enumerate(weather.forecast):
            with f_cols[idx]:
                rain_pill_color = "#2E7D5B" if day.rain_prob < 30 else ("#C58A1A" if day.rain_prob < 60 else "#3B6EA8")
                st.markdown(
                    f"""
                    <div class="forecast-card">
                        <div class="forecast-day-header">{day.date_str}</div>
                        <div class="forecast-condition-icon">{day.icon}</div>
                        <div class="forecast-condition-name">{day.condition}</div>
                        <div class="forecast-temp-range">
                            <span class="forecast-temp-max">{day.temp_max_c:.0f}°</span> / 
                            <span class="forecast-temp-min">{day.temp_min_c:.0f}°C</span>
                        </div>
                        <div class="forecast-rain-pill" style="border-color: {rain_pill_color};">
                            🌧️ {day.rain_prob}% ({day.precipitation_mm:.1f} mm)
                        </div>
                        <div class="forecast-advisory-text">💡 {day.agrarian_advisory}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 7. Active Weather Risk Signals
    # ---------------------------------------------------------
    st.markdown(
        f'<div class="weather-section-title">⚠️ Weather Risk Signals</div>',
        unsafe_allow_html=True,
    )

    if insight.active_risks:
        for risk in insight.active_risks:
            sev_class = f"risk-sev-{risk.severity}"
            st.markdown(
                f"""
                <div class="weather-risk-banner {sev_class}">
                    <div class="weather-risk-header">
                        <span class="weather-risk-title">{risk.risk_type.replace('_', ' ').title()}</span>
                        <span class="weather-risk-badge">{risk.severity.upper()}</span>
                    </div>
                    <div class="weather-risk-desc">{risk.description}</div>
                    <div class="weather-risk-mitigation"><strong>Recommended Action:</strong> {risk.mitigation}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            f"""
            <div class="weather-no-risks-card">
                ● No active weather risk alerts. Weather conditions are favorable for {crop_name}.
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # 8. Contextual Actions & Ask Assistant CTA
    # ---------------------------------------------------------
    assistant_prompt = f"How will today's weather ({weather.condition}, {weather.temperature_c:.0f}°C, {weather.rain_probability}% rain) affect my {crop_name} and irrigation?"
    col_irr, col_ast = st.columns(2)
    with col_irr:
        if st.button("💧 View Irrigation Guidance", key="btn_weather_to_irrigation", use_container_width=True):
            st.session_state.page = "irrigation"
            st.rerun()
    with col_ast:
        st.button(
            f"💬 {t('weather_ask_assistant_btn')}",
            key="btn_weather_ask_assistant",
            on_click=_go_to_assistant,
            args=(assistant_prompt,),
            use_container_width=True,
        )
