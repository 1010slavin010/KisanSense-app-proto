"""Crop Health and Plant Vision screening page for KisanSense.

Provides an intuitive, farmer-friendly interface for visual leaf disease screening
using the offline, deterministic vision intelligence engine (services/vision_service.py).
Integrates farm profile context, live field environmental telemetry, safety gating,
and conservative agronomic screening disclaimers.
"""

from __future__ import annotations

import io
from typing import Any
import streamlit as st
from PIL import Image

from components.breadcrumbs import render_breadcrumbs
from services.farm_service import get_farm_profile, is_profile_configured
from services.vision_service import VisionAnalysisResult, analyze_plant_image
from utils.translations import t


def _go_to_assistant() -> None:
    st.session_state.page = "assistant"


def render() -> None:
    # =========================================================================
    # 1. Header Section
    # =========================================================================
    render_breadcrumbs(t("vision_header"), "vision")

    st.markdown(
        f'<h1 class="ks-page-title hero-title">🌿 {t("vision_header")}</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p class="hero-tagline">{t("vision_subtitle")}</p>',
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
    # 3. Photo Guidance Chips
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

    active_input = uploaded_file or camera_file

    result: VisionAnalysisResult | None = None
    uploaded_bytes: bytes | None = None

    if active_input is not None:
        try:
            uploaded_bytes = active_input.getvalue()
            result = analyze_plant_image(uploaded_bytes, farm_context=farm_ctx)
            st.session_state.latest_vision_result = result
        except Exception as exc:
            st.error(f"Unable to process the image: {exc}")
            result = None
    elif st.session_state.get("latest_vision_result") is not None:
        result = st.session_state.latest_vision_result

    # If no image provided, prompt user (required by test_initial_vision_render_clean)
    if result is None:
        st.info("📷 Upload a clear photo of an affected or healthy crop leaf to begin screening.")
        return

    # =========================================================================
    # 5. Diagnostic Result Card
    # =========================================================================
    col_img, col_result = st.columns([1, 1.35])

    with col_img:
        st.markdown('<div class="vision-card">', unsafe_allow_html=True)
        if uploaded_bytes:
            try:
                st.image(
                    uploaded_bytes,
                    caption="Crop leaf specimen submitted for plant health screening",
                    use_container_width=True,
                )
            except Exception:
                st.write("📷 [Image loaded]")
        else:
            st.write("📷 *Recent scan from this session*")
        
        # Image quality assessment line
        quality_label = "Good" if result.image_quality == "good" else "Poor / Unclear"
        quality_color = "var(--color-good)" if result.image_quality == "good" else "var(--color-alert)"
        st.markdown(
            f'<div style="margin-top: 0.6rem; font-size: 0.85rem; color: var(--color-text-secondary);">'
            f'IMAGE QUALITY: <strong style="color: {quality_color};">{quality_label}</strong>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with col_result:
        # Case A: Quality Gate Rejected
        if not result.success or result.image_quality != "good":
            st.markdown(
                f"""
                <div class="vision-card vision-result-rejected">
                    <div style="font-size: 1.15rem; font-weight: 700; color: var(--color-alert); margin-bottom: 0.4rem;">
                        📷 {t("vision_quality_reject_title")}
                    </div>
                    <p style="color: var(--color-text); margin-bottom: 0.65rem; font-size: 0.92rem;">
                        {result.explanation}
                    </p>
                    <div class="vision-section-box">
                        <strong style="color: var(--color-primary); font-size: 0.85rem;">💡 {t("vision_what_to_do")}:</strong>
                        <p style="margin: 0.25rem 0 0 0; color: var(--color-text); font-size: 0.9rem;">
                            {result.recommended_action}
                        </p>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            return

        # Case B: Diagnostic Result
        conf_pct = int(round(result.confidence * 100))
        if result.confidence_level == "high":
            conf_badge = f'<span class="vision-badge-high">● High Confidence ({conf_pct}%)</span>'
        elif result.confidence_level == "moderate":
            conf_badge = f'<span class="vision-badge-moderate">● Moderate Confidence ({conf_pct}%)</span>'
        else:
            conf_badge = f'<span class="vision-badge-low">● Low Confidence ({conf_pct}%)</span>'

        if result.healthy:
            card_class = "vision-result-healthy"
            headline_text = t("vision_healthy_title")
            headline_color = "var(--color-good)"
        else:
            card_class = "vision-result-warning"
            headline_text = t("vision_warning_title")
            headline_color = "var(--color-warning)"

        category_label = result.category.replace("_", " ").title()

        symptoms_list = getattr(result, "symptoms_detected", [])
        symptoms_str = ", ".join(s.replace("_", " ").title() for s in symptoms_list) if symptoms_list else t("vision_no_symptoms")

        urgency_key = f"vision_urgency_{getattr(result, 'treatment_urgency', 'none')}"
        urgency_label = t(urgency_key)

        affected_ratio = getattr(result, "affected_foliage_ratio", 0.0)
        affected_str = f" • 🍃 Affected foliage: ~{affected_ratio*100:.1f}%" if affected_ratio > 0.0 else ""

        st.markdown(
            f"""
            <div class="vision-card {card_class}">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.4rem;">
                    <span style="font-size: 0.85rem; font-weight: 700; color: {headline_color}; text-transform: uppercase; letter-spacing: 0.04em;">
                        ● CROP HEALTH — {headline_text}
                    </span>
                    {conf_badge}
                </div>
                <div style="font-size: 1.35rem; font-weight: 700; color: var(--color-text); margin-bottom: 0.35rem;">
                    {result.diagnosis}
                </div>
                <div style="font-size: 0.84rem; color: var(--color-text-secondary); margin-bottom: 0.75rem;">
                    🌾 <strong>{result.crop}</strong> • Category: <strong>{category_label}</strong> • Urgency: <strong>{urgency_label}</strong>{affected_str}
                </div>
                <div class="vision-section-box">
                    <div style="font-size: 0.82rem; font-weight: 700; color: var(--color-text); text-transform: uppercase; letter-spacing: 0.03em;">
                        🔬 Symptoms Detected
                    </div>
                    <p style="margin: 0.2rem 0 0.5rem 0; color: var(--color-text-secondary); font-size: 0.88rem;">
                        {symptoms_str}
                    </p>
                    <div style="font-size: 0.82rem; font-weight: 700; color: var(--color-text); text-transform: uppercase; letter-spacing: 0.03em;">
                        🔍 Screening Assessment
                    </div>
                    <p style="margin: 0.2rem 0 0.5rem 0; color: var(--color-text); font-size: 0.9rem; line-height: 1.45;">
                        {result.explanation}
                    </p>
                    <div style="font-size: 0.82rem; font-weight: 700; color: var(--color-primary); text-transform: uppercase; letter-spacing: 0.03em;">
                        🌱 Recommended Cultural Action
                    </div>
                    <p style="margin: 0.2rem 0 0 0; color: var(--color-text); font-size: 0.9rem; line-height: 1.45;">
                        {result.recommended_action}
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.button(
            f"💬 {t('vision_ask_assistant_btn')}",
            key="btn_ask_vision_assistant",
            on_click=_go_to_assistant,
            use_container_width=True,
        )

    # =========================================================================
    # 6. Safety & Conservative Agronomic Disclaimer
    # =========================================================================
    st.markdown(
        """
        <div class="vision-disclaimer">
            <strong>⚠️ AI Screening Notice:</strong> This assessment is an automated computer vision screening tool intended for early field detection and agronomic advisory. It is not a definitive laboratory diagnostic. Confirm severe symptoms with local agricultural extension officers before taking major chemical interventions.
        </div>
        """,
        unsafe_allow_html=True,
    )
