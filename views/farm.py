"""Camera / Crop Scan view for KisanSense.

Provides an intuitive, mobile-first plant and leaf scanning interface.
Enables farmers to:
1. Upload a picture of a plant or leaf from their device (JPG, JPEG, PNG, WEBP).
2. Take a photo using their device built-in camera/webcam.
3. Preview the captured/uploaded image and confirm readiness.
4. Run foliar vision analysis via the existing offline deterministic vision engine.
5. Display a clear, farmer-friendly result card with conservative recommendations.
6. Retain operational farm profile data and settings in a collapsible expander.
"""

from __future__ import annotations

import io
from typing import Any
import streamlit as st

from components.breadcrumbs import render_breadcrumbs
from services.farm_service import (
    AREA_UNITS,
    COMMON_CROPS,
    GROWTH_STAGES,
    IRRIGATION_METHODS,
    SOIL_TYPES,
    FarmProfile,
    get_farm_context,
    get_farm_profile,
    is_profile_configured,
    save_farm_profile,
    validate_farm_profile,
)
from services.vision_service import VisionAnalysisResult, analyze_plant_image
from utils.translations import t


def _go_to_assistant() -> None:
    st.session_state.page = "assistant"


def _render_guidance_tips() -> None:
    """Render a compact, farmer-friendly photo quality guidance section."""
    st.markdown(
        f"""
        <div class="insight-card" style="margin-bottom: 1.25rem;">
            <div style="font-weight: 700; font-size: 0.92rem; color: var(--color-primary); margin-bottom: 0.45rem; display: flex; align-items: center; gap: 6px;">
                💡 {t('camera_scan_tips_title')}
            </div>
            <div style="font-size: 0.88rem; color: var(--color-text-secondary); line-height: 1.55;">
                • {t('camera_scan_tip_daylight')}<br/>
                • {t('camera_scan_tip_focus')}<br/>
                • {t('camera_scan_tip_area')}<br/>
                • {t('camera_scan_tip_shadows')}<br/>
                • {t('camera_scan_tip_sides')}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_result_card(result: VisionAnalysisResult, image_bytes: bytes | None) -> None:
    """Render a clean, conservative, farmer-friendly diagnostic result card."""
    col_img, col_diag = st.columns([1, 1.35])

    with col_img:
        st.markdown('<div class="vision-card">', unsafe_allow_html=True)
        if image_bytes:
            try:
                st.image(
                    image_bytes,
                    caption="Scanned crop leaf specimen",
                    use_container_width=True,
                )
            except Exception:
                st.write("📷 [Image Preview]")
        else:
            st.write("📷 *Recent scan from this session*")

        quality_label = "Good" if result.image_quality == "good" else "Poor / Unclear"
        quality_color = "var(--color-good)" if result.image_quality == "good" else "var(--color-alert)"
        st.markdown(
            f'<div style="margin-top: 0.6rem; font-size: 0.85rem; color: var(--color-text-secondary);">'
            f'IMAGE QUALITY: <strong style="color: {quality_color};">{quality_label}</strong>'
            f'</div>',
            unsafe_allow_html=True,
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with col_diag:
        # Case A: Quality Gate Failed / Low Quality
        if not result.success or result.image_quality != "good":
            reject_elements = [
                '<div class="vision-card vision-result-rejected">',
                f'<div style="font-size: 1.15rem; font-weight: 700; color: var(--color-alert); margin-bottom: 0.4rem;">📷 {t("vision_quality_reject_title")}</div>',
                f'<p style="color: var(--color-text); margin-bottom: 0.65rem; font-size: 0.92rem;">{result.explanation}</p>',
                '<div class="vision-section-box">',
                f'<strong style="color: var(--color-primary); font-size: 0.85rem;">💡 {t("camera_scan_action")}:</strong>',
                f'<p style="margin: 0.25rem 0 0 0; color: var(--color-text); font-size: 0.9rem;">{t("camera_scan_uncertain")} {result.recommended_action}</p>',
                '</div>',
                '</div>',
            ]
            st.markdown("".join(reject_elements), unsafe_allow_html=True)
            return

        # Case B: Successful Diagnostic
        conf_pct = int(round(result.confidence * 100))
        if result.confidence_level == "high":
            conf_badge = f'<span class="vision-badge-high">● High Confidence ({conf_pct}%)</span>'
        elif result.confidence_level == "moderate":
            conf_badge = f'<span class="vision-badge-moderate">● Moderate Confidence ({conf_pct}%)</span>'
        else:
            conf_badge = f'<span class="vision-badge-low">● Low Confidence ({conf_pct}%)</span>'

        is_ml = getattr(result, "inference_backend", "") == "ml_keras"
        detection_method = "AI Crop Model" if is_ml else "Local Vision Engine"
        method_badge = (
            '<span style="background: rgba(16, 185, 129, 0.15); color: var(--color-primary); font-weight: 600; font-size: 0.76rem; padding: 2px 8px; border-radius: 9999px; border: 1px solid rgba(16, 185, 129, 0.3);">🤖 AI Crop Model</span>'
            if is_ml
            else '<span style="background: rgba(100, 116, 139, 0.15); color: var(--color-text-secondary); font-weight: 600; font-size: 0.76rem; padding: 2px 8px; border-radius: 9999px; border: 1px solid rgba(100, 116, 139, 0.3);">⚙️ Local Vision Engine</span>'
        )

        low_conf_banner = ""
        if result.confidence < 0.60 or result.confidence_level == "low":
            low_conf_banner = (
                '<div style="margin: 0.6rem 0; padding: 0.65rem 0.85rem; border-radius: 8px; '
                'background: rgba(217, 119, 6, 0.12); border: 1px solid rgba(217, 119, 6, 0.3); '
                'color: var(--color-warning); font-size: 0.86rem; line-height: 1.45;">'
                '<strong>⚠️ Low Confidence Notice:</strong> AI confidence is low. Please take a clearer photo in good natural daylight or consult a local agriculture expert.'
                '</div>'
            )

        if result.healthy:
            card_class = "vision-result-healthy"
            status_text = "Healthy"
            headline_color = "var(--color-good)"
        else:
            card_class = "vision-result-warning"
            category_clean = result.category.replace("_", " ").title()
            status_text = f"Possible {category_clean}"
            headline_color = "var(--color-warning)"

        symptoms_list = getattr(result, "symptoms_detected", [])
        symptoms_str = (
            ", ".join(s.replace("_", " ").title() for s in symptoms_list)
            if symptoms_list
            else t("vision_no_symptoms")
        )

        card_elements = [
            f'<div class="vision-card {card_class}">',
            '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem; flex-wrap: wrap; gap: 0.4rem;">',
            f'<span style="font-size: 0.85rem; font-weight: 700; color: {headline_color}; text-transform: uppercase; letter-spacing: 0.04em;">',
            f'🌿 {t("camera_scan_result_title")} — {status_text}',
            '</span>',
            f'<div style="display: flex; align-items: center; gap: 6px;">{method_badge}{conf_badge}</div>',
            '</div>',
            f'<div style="font-size: 1.35rem; font-weight: 700; color: var(--color-text); margin-bottom: 0.25rem;">{result.diagnosis}</div>',
            f'<div style="font-size: 0.84rem; color: var(--color-text-secondary); margin-bottom: 0.65rem;">',
            f'🌾 <strong>{result.crop}</strong> • Category: <strong>{result.category.replace("_", " ").title()}</strong> • Method: <strong>{detection_method}</strong>',
            '</div>',
            low_conf_banner,
            '<div class="vision-section-box">',
            f'<div style="font-size: 0.82rem; font-weight: 700; color: var(--color-text); text-transform: uppercase; letter-spacing: 0.03em;">🔬 {t("camera_scan_observed")}</div>',
            f'<p style="margin: 0.2rem 0 0.45rem 0; color: var(--color-text-secondary); font-size: 0.88rem;">{symptoms_str}</p>',
            f'<p style="margin: 0.2rem 0 0.55rem 0; color: var(--color-text); font-size: 0.9rem; line-height: 1.45;"><strong>What this means:</strong> {result.explanation}</p>',
            f'<div style="font-size: 0.82rem; font-weight: 700; color: var(--color-primary); text-transform: uppercase; letter-spacing: 0.03em;">🌱 {t("camera_scan_action")}</div>',
            f'<p style="margin: 0.2rem 0 0 0; color: var(--color-text); font-size: 0.9rem; line-height: 1.45;"><strong>What to do:</strong> {result.recommended_action}</p>',
            '</div>',
            '</div>',
        ]
        st.markdown("".join(card_elements), unsafe_allow_html=True)

        class_probs = getattr(result, "class_probabilities", {})
        if class_probs:
            with st.expander("📊 View Model Prediction Probabilities", expanded=False):
                for cname, cprob in class_probs.items():
                    clean_cname = cname.replace("___", " - ").replace("_", " ")
                    st.progress(cprob, text=f"{clean_cname}: {cprob * 100:.1f}%")

        st.button(
            f"💬 {t('camera_scan_ask_assistant')}",
            key="btn_ask_camera_assistant",
            on_click=_go_to_assistant,
            use_container_width=True,
        )

    st.markdown(
        '<div class="vision-disclaimer">'
        '<strong>⚠️ AI Screening Notice:</strong> This assessment is an automated computer vision screening tool intended for early field detection and agronomic advisory. It is not a definitive laboratory diagnostic. Confirm severe symptoms with local agricultural extension officers before taking major chemical interventions.'
        '</div>',
        unsafe_allow_html=True,
    )


def _render_profile_overview(profile: FarmProfile) -> None:
    """Render a clean summary card of the active farm profile."""
    farmer_str = profile.farmer_name or "Not set"
    farm_str = profile.farm_name or "My Farm"
    loc_str = profile.location or "Location not set"
    area_str = (
        f"{profile.farm_area:.1f} {profile.area_unit}"
        if profile.farm_area is not None
        else "Not specified"
    )
    variety_info = f" ({profile.crop_variety})" if profile.crop_variety else ""

    st.markdown(
        f"""
        <div class="metric-card metric-card-good" style="margin-bottom: 1.25rem;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 8px;">
                <div>
                    <div class="metric-card-title">{t("farm_overview_title")}</div>
                    <div class="metric-card-value" style="font-size: 1.5rem; margin-bottom: 0.2rem;">
                        {farm_str}
                    </div>
                    <div style="color: var(--color-text-secondary); font-size: 0.9rem;">
                        Farmer: <strong>{farmer_str}</strong> • Location: <strong>{loc_str}</strong>
                    </div>
                </div>
                <span class="badge badge-good">● Active Farm Context</span>
            </div>
            <p class="metric-card-description" style="margin-top: 0.65rem;">
                {t("farm_overview_subtitle")}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(
            f"""
            <div class="metric-card" style="margin-bottom: 1rem;">
                <div class="metric-card-title">Crop Information</div>
                <div style="font-size: 1.2rem; font-weight: 700; color: var(--color-primary-dark); margin: 0.25rem 0;">
                    🌾 {profile.crop}{variety_info}
                </div>
                <div style="font-size: 0.86rem; color: var(--color-text-secondary);">
                    Growth Stage: <strong>{profile.growth_stage or "Not specified"}</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f"""
            <div class="metric-card" style="margin-bottom: 1rem;">
                <div class="metric-card-title">Soil & Irrigation</div>
                <div style="font-size: 1.2rem; font-weight: 700; color: var(--color-text); margin: 0.25rem 0;">
                    🪨 {profile.soil_type or "General Soil"}
                </div>
                <div style="font-size: 0.86rem; color: var(--color-text-secondary);">
                    Method: <strong>{profile.irrigation_method or "Standard"}</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f"""
            <div class="metric-card" style="margin-bottom: 1rem;">
                <div class="metric-card-title">Farm Area & Bounds</div>
                <div style="font-size: 1.2rem; font-weight: 700; color: var(--color-text); margin: 0.25rem 0;">
                    📐 {area_str}
                </div>
                <div style="font-size: 0.86rem; color: var(--color-text-secondary);">
                    Region: <strong>{loc_str}</strong>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    col_edit, col_wx = st.columns([1, 1.2])
    with col_edit:
        if st.button(f"✏️ {t('farm_edit_button')}", key="btn_edit_profile", use_container_width=True):
            st.session_state.edit_farm_profile = True
            st.rerun()
    with col_wx:
        if st.button("🌤️ Check Farm Weather", key="btn_farm_to_weather", use_container_width=True):
            st.session_state.page = "weather"
            st.rerun()


def _render_profile_form(profile: FarmProfile, is_first_time: bool) -> None:
    """Render the farm profile entry and update form."""
    if is_first_time:
        st.info(f"💡 {t('home_empty_profile_prompt')}")

    st.markdown(
        f'<div style="font-size: 1.2rem; font-weight: 700; margin-bottom: 0.75rem; color: var(--color-text);">'
        f'{t("farm_form_title")}'
        f'</div>',
        unsafe_allow_html=True,
    )

    with st.form("farm_profile_form", clear_on_submit=False):
        st.markdown(
            '<div style="font-weight: 650; font-size: 0.92rem; color: var(--color-primary); margin-bottom: 0.4rem; text-transform: uppercase; letter-spacing: 0.04em;">'
            'Farmer & Farm Information'
            '</div>',
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            farmer_name = st.text_input(
                t("farmer_name_label"),
                value=profile.farmer_name,
                placeholder=t("farmer_name_placeholder"),
            )
        with c2:
            farm_name = st.text_input(
                t("farm_name_label"),
                value=profile.farm_name,
                placeholder=t("farm_name_placeholder"),
            )

        st.markdown(
            '<div style="font-weight: 650; font-size: 0.92rem; color: var(--color-primary); margin: 0.6rem 0 0.4rem 0; text-transform: uppercase; letter-spacing: 0.04em;">'
            'Crop Information'
            '</div>',
            unsafe_allow_html=True,
        )
        c3, c4 = st.columns(2)
        with c3:
            crop_options = list(COMMON_CROPS)
            custom_crop = ""
            if profile.crop and profile.crop in crop_options:
                crop_idx = crop_options.index(profile.crop)
            elif profile.crop:
                crop_options.insert(0, profile.crop)
                crop_idx = 0
            else:
                crop_idx = 2  # Default to Tomato

            selected_crop = st.selectbox(t("crop_label"), options=crop_options, index=crop_idx)
            if selected_crop == "Other":
                custom_crop = st.text_input("Enter Crop Name", value=profile.crop if profile.crop not in COMMON_CROPS else "")

        with c4:
            crop_variety = st.text_input(
                t("crop_variety_label"),
                value=profile.crop_variety,
                placeholder=t("crop_variety_placeholder"),
            )

        c5, c6 = st.columns(2)
        with c5:
            stage_idx = (
                GROWTH_STAGES.index(profile.growth_stage)
                if profile.growth_stage in GROWTH_STAGES
                else 2
            )
            growth_stage = st.selectbox(
                t("growth_stage_label"),
                options=GROWTH_STAGES,
                index=stage_idx,
            )
        with c6:
            soil_idx = (
                SOIL_TYPES.index(profile.soil_type)
                if profile.soil_type in SOIL_TYPES
                else 0
            )
            soil_type = st.selectbox(
                t("soil_type_label"),
                options=SOIL_TYPES,
                index=soil_idx,
            )

        st.markdown(
            '<div style="font-weight: 650; font-size: 0.92rem; color: var(--color-primary); margin: 0.6rem 0 0.4rem 0; text-transform: uppercase; letter-spacing: 0.04em;">'
            'Farm Details & Location'
            '</div>',
            unsafe_allow_html=True,
        )
        c7, c8 = st.columns(2)
        with c7:
            area_val = profile.farm_area if profile.farm_area is not None else 5.0
            farm_area = st.number_input(
                t("farm_area_label"),
                min_value=0.0,
                max_value=10000.0,
                value=float(area_val),
                step=0.5,
            )
        with c8:
            unit_idx = (
                AREA_UNITS.index(profile.area_unit)
                if profile.area_unit in AREA_UNITS
                else 0
            )
            area_unit = st.selectbox(
                t("area_unit_label"),
                options=AREA_UNITS,
                index=unit_idx,
            )

        c9, c10 = st.columns(2)
        with c9:
            irrig_idx = (
                IRRIGATION_METHODS.index(profile.irrigation_method)
                if profile.irrigation_method in IRRIGATION_METHODS
                else 0
            )
            irrigation_method = st.selectbox(
                t("irrigation_method_label"),
                options=IRRIGATION_METHODS,
                index=irrig_idx,
            )
        with c10:
            location = st.text_input(
                t("location_label"),
                value=profile.location,
                placeholder=t("location_placeholder"),
            )

        st.markdown('<div style="height: 0.5rem;"></div>', unsafe_allow_html=True)
        submitted = st.form_submit_button(t("save_profile_button"), use_container_width=True)

        if submitted:
            final_crop = custom_crop.strip() if selected_crop == "Other" and custom_crop.strip() else selected_crop

            candidate_data = {
                "farmer_name": farmer_name.strip(),
                "farm_name": farm_name.strip(),
                "crop": final_crop,
                "crop_variety": crop_variety.strip(),
                "growth_stage": growth_stage,
                "soil_type": soil_type,
                "farm_area": float(farm_area) if farm_area is not None else None,
                "area_unit": area_unit,
                "irrigation_method": irrigation_method,
                "location": location.strip(),
            }

            is_valid, errors = validate_farm_profile(candidate_data)
            if not is_valid:
                for err_msg in errors.values():
                    st.error(f"⚠️ {err_msg}")
            else:
                updated_profile = FarmProfile.from_dict(candidate_data)
                save_farm_profile(updated_profile)
                st.session_state.edit_farm_profile = False
                st.success(t("profile_saved_success"))
                st.rerun()


def render() -> None:
    profile = get_farm_profile()
    configured = is_profile_configured(profile)

    render_breadcrumbs(t("camera_scan_title"), "farm")

    # =========================================================================
    # 1. Header & Page Tagline (One clear H1)
    # =========================================================================
    st.markdown(
        f'<h1 class="ks-page-title hero-title">📷 {t("camera_scan_title")}</h1>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<p class="hero-tagline">{t("camera_scan_subtitle")}</p>',
        unsafe_allow_html=True,
    )

    # Active Crop Context Badge
    if configured and profile.crop:
        crop_badge = (
            f'<div class="vision-context-banner">'
            f'🌾 {t("vision_current_crop")}: <strong>{profile.crop}</strong>'
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
    # 2. Photo Quality Guidance
    # =========================================================================
    _render_guidance_tips()

    # =========================================================================
    # 3. Dual Input Methods: Upload or Camera
    # =========================================================================
    tab_upload, tab_camera = st.tabs(
        [f"📁 {t('camera_scan_upload_tab')}", f"📷 {t('camera_scan_camera_tab')}"]
    )

    uploaded_file = None
    with tab_upload:
        uploaded_file = st.file_uploader(
            t("camera_scan_upload_label"),
            type=["jpg", "jpeg", "png", "webp"],
            help=t("camera_scan_upload_help"),
            key="camera_scan_uploader",
        )

    camera_file = None
    with tab_camera:
        camera_file = st.camera_input(
            t("camera_scan_camera_label"),
            help=t("camera_scan_camera_help"),
            key="camera_scan_camera",
        )

    active_file = uploaded_file or camera_file
    active_bytes: bytes | None = None

    if active_file is not None:
        try:
            active_bytes = active_file.getvalue()
            # If the user changed or uploaded a new image, update active image
            if st.session_state.get("farm_scan_active_bytes") != active_bytes:
                st.session_state.farm_scan_active_bytes = active_bytes
                # Clear previous result on fresh image input
                st.session_state.camera_scan_result = None
        except Exception:
            active_bytes = None
    elif st.session_state.get("farm_scan_active_bytes") is not None:
        active_bytes = st.session_state.farm_scan_active_bytes

    # =========================================================================
    # 4. Preview & Analyze CTA Flow
    # =========================================================================
    if active_bytes:
        st.success(f"✅ {t('camera_scan_ready')}")
        
        # Display image preview with reasonable width
        col_prev1, col_prev2, col_prev3 = st.columns([1, 2, 1])
        with col_prev2:
            try:
                st.image(
                    active_bytes,
                    caption="Image ready for crop health analysis",
                    use_container_width=True,
                )
            except Exception:
                st.write("📷 [Image loaded]")

        # Main CTA: Analyze Crop (explicit button press prevents unneeded processing)
        if st.button(
            f"🔍 {t('camera_scan_analyze_btn')}",
            key="btn_analyze_crop",
            type="primary",
            use_container_width=True,
        ):
            try:
                farm_ctx = get_farm_context()
                with st.spinner("Analyzing crop leaf symptoms..."):
                    result = analyze_plant_image(active_bytes, farm_context=farm_ctx)
                st.session_state.latest_vision_result = result
                st.session_state.camera_scan_result = result
            except Exception as exc:
                st.error(f"{t('camera_scan_error')}: {exc}")
    else:
        st.info(f"📷 {t('camera_scan_no_image')}")

    # =========================================================================
    # 5. Crop Health Result Card
    # =========================================================================
    current_result: VisionAnalysisResult | None = st.session_state.get("camera_scan_result")
    if current_result is None and st.session_state.get("latest_vision_result") is not None:
        # Fall back to latest vision result if set earlier
        current_result = st.session_state.latest_vision_result

    if current_result is not None:
        st.markdown('<div class="section-spacer" style="height: 0.5rem;"></div>', unsafe_allow_html=True)
        _render_result_card(current_result, active_bytes)

    # =========================================================================
    # 6. Farm Profile Settings & Operational Context (Preserved in Expander)
    # =========================================================================
    st.markdown('<div class="section-spacer" style="height: 1.5rem;"></div>', unsafe_allow_html=True)
    if "edit_farm_profile" not in st.session_state:
        st.session_state.edit_farm_profile = not configured

    with st.expander(
        f"🌾 {t('camera_scan_profile_expander')}",
        expanded=st.session_state.get("edit_farm_profile", False),
    ):
        if configured and not st.session_state.get("edit_farm_profile", False):
            _render_profile_overview(profile)
        else:
            _render_profile_form(profile, is_first_time=(not configured))
