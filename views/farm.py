"""Farm Profile view for KisanSense.

Enables farmers to view, configure, and update their farm profile (farmer name,
farm name, crop, growth stage, soil type, area, irrigation method, and location).
Organized cleanly into Farmer Information, Crop Information, and Farm Details.
All state persists in st.session_state.farm_profile across reruns and navigation.
"""

from __future__ import annotations

import streamlit as st

from components.breadcrumbs import render_breadcrumbs
from services.farm_service import (
    AREA_UNITS,
    COMMON_CROPS,
    GROWTH_STAGES,
    IRRIGATION_METHODS,
    SOIL_TYPES,
    FarmProfile,
    get_farm_profile,
    is_profile_configured,
    save_farm_profile,
    validate_farm_profile,
)
from utils.translations import t


def _render_profile_overview(profile: FarmProfile) -> None:
    """Render a clean enterprise summary card of the active farm profile."""
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

    render_breadcrumbs(t("farm_title"), "farm")

    if "edit_farm_profile" not in st.session_state:
        st.session_state.edit_farm_profile = not configured

    st.markdown(f'<h1 class="ks-page-title hero-title">{t("farm_title")}</h1>', unsafe_allow_html=True)
    st.markdown(f'<p class="hero-tagline">{t("farm_subtitle")}</p>', unsafe_allow_html=True)
    st.markdown('<div class="section-spacer" style="height: 1rem;"></div>', unsafe_allow_html=True)

    if configured and not st.session_state.edit_farm_profile:
        _render_profile_overview(profile)
    else:
        _render_profile_form(profile, is_first_time=(not configured))
