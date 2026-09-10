"""Crop Health and Plant Vision analysis page for KisanSense.

Provides an intuitive, farmer-friendly interface for visual leaf disease screening
using the offline, deterministic vision intelligence engine (services/vision_service.py).
Integrates farm profile context, live field environmental telemetry, safety gating,
and seamless handoff to the KisanSense AI Assistant.
"""

from __future__ import annotations

import io
from typing import Any
import streamlit as st
from PIL import Image

from services.farm_service import get_farm_profile, is_profile_configured
from services.vision_service import VisionAnalysisResult, analyze_plant_image
from utils.translations import t


def _go_to_assistant() -> None:
    st.session_state.page = "assistant"


def render() -> None:
    # =========================================================================
    # 1. Header Section
    # =========================================================================
    st.markdown(
        f'<div class="vision-header-title">🌿 {t("vision_header")}</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="vision-header-subtitle">{t("vision_subtitle")}</div>',
        unsafe_allow_html=True,
    )

    # =========================================================================
    # 2. Farm Context Banner
    # =========================================================================
    profile = get_farm_profile()
    farm_ctx = profile.to_dict()
    has_crop = is_profile_configured(profile)

    if has_crop:
        crop_name = profile.crop
        crop_badge = (
            f'<div class="vision-context-banner">'
            f'🌾 {t("vision_current_crop")}: <strong>{crop_name}</strong>'
            f'</div>'
        )
    else:
        crop_badge = (
            f'<div class="vision-context-banner" style="opacity: 0.85;">'
            f'🌾 {t("vision_generic_crop")}'
            f'</div>'
        )
    st.markdown(crop_badge, unsafe_allow_html=True)

    # =========================================================================
    # 3. Simple Photo Guidance
    # =========================================================================
    st.markdown(
        f"""
        <div class="vision-guidance-grid">
            <div class="vision-guidance-item">📸 {t("vision_tip_focus")}</div>
            <div class="vision-guidance-item">☀️ {t("vision_tip_daylight")}</div>
            <div class="vision-guidance-item">🌿 {t("vision_tip_frame")}</div>
            <div class="vision-guidance-item">🚫 {t("vision_tip_shadows")}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # =========================================================================
    # 4. Photo Upload & Camera Input Area
    # =========================================================================
    tab_upload, tab_camera = st.tabs([f"📁 {t('vision_tab_upload')}", f"📷 {t('vision_tab_camera')}"])

    uploaded_file = None
    with tab_upload:
        uploaded_file = st.file_uploader(
            t("vision_upload_label"),
            type=["jpg", "jpeg", "png", "webp"],
            help=t("vision_upload_help"),
            key="vision_uploader",
        )

    camera_file = None
    with tab_camera:
        camera_file = st.camera_input(
            t("vision_camera_label"),
            help=t("vision_camera_help"),
            key="vision_camera",
        )

    # Active file from either uploader or camera
    active_input = uploaded_file or camera_file

    # Evaluate analysis upon upload or camera capture
    result: VisionAnalysisResult | None = None
    uploaded_bytes: bytes | None = None

    if active_input is not None:
        try:
            uploaded_bytes = active_input.getvalue()
            # Analyze image with local vision engine and active farm profile
            result = analyze_plant_image(uploaded_bytes, farm_context=farm_ctx)
            # Store in session state for Assistant sharing and session persistence
            st.session_state.latest_vision_result = result
        except Exception as exc:
            st.error(f"Unable to process the image: {exc}")
            result = None
    elif st.session_state.get("latest_vision_result") is not None:
        # Retain last result during the browser session if no new file is uploaded
        result = st.session_state.latest_vision_result

    # If no image provided and no previous session result, display helpful prompt
    if result is None:
        st.info("📷 Upload a clear photo of an affected or healthy crop leaf to begin screening.")
        return

    # =========================================================================
    # 5. Image Display & Quality Gate / Results
    # =========================================================================
    col_img, col_result = st.columns([1, 1.4])

    with col_img:
        st.markdown('<div class="vision-card">', unsafe_allow_html=True)
        if uploaded_bytes:
            try:
                st.image(uploaded_bytes, caption="Uploaded Leaf Photo", use_container_width=True)
            except Exception:
                st.write("📷 [Image loaded]")
        else:
            st.write("📷 *Recent scan from this session*")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_result:
        # ---------------------------------------------------------------------
        # Case A: Image Quality Gate Rejected
        # ---------------------------------------------------------------------
        if not result.success or result.image_quality != "good":
            st.markdown(
                f"""
                <div class="vision-card vision-result-rejected">
                    <div style="font-size: 1.25rem; font-weight: 600; color: var(--color-alert); margin-bottom: 0.5rem;">
                        📷 {t("vision_quality_reject_title")}
                    </div>
                    <p style="color: var(--color-text); margin-bottom: 0.75rem; font-size: 0.95rem;">
                        {result.explanation}
                    </p>
                    <div class="vision-section-box">
                        <strong style="color: var(--color-primary); font-size: 0.88rem;">💡 {t("vision_what_to_do")}:</strong>
                        <p style="margin: 0.3rem 0 0 0; color: var(--color-text); font-size: 0.92rem;">
                            {result.recommended_action}
                        </p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            return

        # ---------------------------------------------------------------------
        # Case B: Diagnostic Result (Healthy or Symptom Detected)
        # ---------------------------------------------------------------------
        # Confidence Badge
        conf_pct = int(round(result.confidence * 100))
        if result.confidence_level == "high":
            conf_badge = f'<span class="vision-badge-high">🟢 {t("vision_conf_high")} ({conf_pct}%)</span>'
        elif result.confidence_level == "moderate":
            conf_badge = f'<span class="vision-badge-moderate">🟡 {t("vision_conf_moderate")} ({conf_pct}%)</span>'
        else:
            conf_badge = f'<span class="vision-badge-low">🟠 {t("vision_conf_low")} ({conf_pct}%)</span>'

        if result.healthy:
            # Healthy Foliage
            card_class = "vision-result-healthy"
            headline_icon = "🟢"
            headline_text = t("vision_healthy_title")
            headline_color = "var(--color-good)"
        else:
            # Disease / Stress Detected
            card_class = "vision-result-warning"
            headline_icon = "⚠️"
            headline_text = t("vision_warning_title")
            headline_color = "var(--color-warning)"

        category_label = result.category.replace("_", " ").title()

        # Symptoms and Urgency badges
        symptoms_list = getattr(result, "symptoms_detected", [])
        if symptoms_list:
            symptoms_str = ", ".join(s.replace("_", " ").title() for s in symptoms_list)
        else:
            symptoms_str = t("vision_no_symptoms")

        urgency_key = f"vision_urgency_{getattr(result, 'treatment_urgency', 'none')}"
        urgency_label = t(urgency_key)

        affected_ratio = getattr(result, "affected_foliage_ratio", 0.0)
        affected_str = f" • 🍃 {t('vision_affected_area')}: ~{affected_ratio*100:.1f}%" if affected_ratio > 0.0 else ""

        st.markdown(
            f"""
            <div class="vision-card {card_class}">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.6rem; flex-wrap: wrap; gap: 0.5rem;">
                    <span style="font-size: 1.15rem; font-weight: 600; color: {headline_color};">
                        {headline_icon} {headline_text}
                    </span>
                    {conf_badge}
                </div>
                <div style="font-size: 1.45rem; font-weight: 700; color: var(--color-text); margin-bottom: 0.4rem;">
                    {result.diagnosis}
                </div>
                <div style="font-size: 0.85rem; color: var(--color-text-muted); margin-bottom: 0.85rem;">
                    🌾 <strong>{result.crop}</strong> • 🏷️ {t("vision_category")}: {category_label} • ⚡ {t("vision_urgency_title")}: <strong>{urgency_label}</strong>{affected_str}
                </div>
                <div class="vision-section-box">
                    <strong style="color: var(--color-text); font-size: 0.88rem;">🔬 {t("vision_symptoms_detected")}:</strong>
                    <p style="margin: 0.2rem 0 0.5rem 0; color: var(--color-text-muted); font-size: 0.88rem;">
                        {symptoms_str}
                    </p>
                    <strong style="color: var(--color-text); font-size: 0.88rem;">🔍 {t("vision_what_found")}:</strong>
                    <p style="margin: 0.25rem 0 0.6rem 0; color: var(--color-text); font-size: 0.92rem; line-height: 1.45;">
                        {result.explanation}
                    </p>
                    <strong style="color: var(--color-primary); font-size: 0.88rem;">🌱 {t("vision_what_to_do")}:</strong>
                    <p style="margin: 0.25rem 0 0 0; color: var(--color-text); font-size: 0.92rem; line-height: 1.45;">
                        {result.recommended_action}
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Hand-off to Assistant Button
        st.button(
            f"💬 {t('vision_ask_assistant_btn')}",
            key="btn_ask_vision_assistant",
            on_click=_go_to_assistant,
            use_container_width=True,
        )

    # =========================================================================
    # 6. Current Farm Conditions & Contextual Insight
    # =========================================================================
    try:
        from services.sensor_service import get_current_sensor_data
        from services.farm_intelligence import evaluate_farm_intelligence

        sensor_reading = st.session_state.get("sensor_reading")
        if sensor_reading is None:
            sensor_reading = get_current_sensor_data(farm_context=farm_ctx)

        if sensor_reading is not None and sensor_reading.is_online:
            st.markdown(f'<div class="insights-header">🌡️ {t("vision_farm_conditions_title")}</div>', unsafe_allow_html=True)
            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                st.markdown(
                    f"""
                    <div class="insight-card">
                        <div class="insight-title">🌱 {t("card_soil_title")}</div>
                        <div style="font-size: 1.25rem; font-weight: 700; color: var(--color-text);">{sensor_reading.soil_moisture:.0f}%</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col_s2:
                st.markdown(
                    f"""
                    <div class="insight-card">
                        <div class="insight-title">🌡️ {t("card_temp_title")}</div>
                        <div style="font-size: 1.25rem; font-weight: 700; color: var(--color-text);">{sensor_reading.temperature:.0f}°C</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col_s3:
                st.markdown(
                    f"""
                    <div class="insight-card">
                        <div class="insight-title">💧 {t("card_humidity_title")}</div>
                        <div style="font-size: 1.25rem; font-weight: 700; color: var(--color-text);">{sensor_reading.humidity:.0f}%</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # Contextual note if high humidity might favor fungal development
            if sensor_reading.humidity > 70.0 and not result.healthy and result.category == "fungal":
                st.caption("💧 *Note: Field humidity is elevated (>70%), which creates favorable conditions for foliar fungal spread. Ensure canopy ventilation and reduce sprinkler watering.*")
    except Exception:
        pass

    # =========================================================================
    # 7. Safety & Agronomic Disclaimers
    # =========================================================================
    if result.warnings:
        warning_lines = "<br/>".join(f"• {w}" for w in result.warnings)
        st.markdown(
            f"""
            <div class="vision-disclaimer">
                <strong>⚠️ {t("vision_disclaimer_title")}:</strong><br/>
                {warning_lines}
            </div>
            """,
            unsafe_allow_html=True,
        )
