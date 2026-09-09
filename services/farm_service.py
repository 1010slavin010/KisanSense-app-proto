"""Farm profile management and farm context provider for KisanSense.

Manages the farmer's operational profile (crop, soil, growth stage, irrigation method,
location, and area) within Streamlit session state and provides clean, decoupled
context dictionaries for consumption by chatbot, irrigation, alerts, and home views.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
import streamlit as st


@dataclass
class FarmProfile:
    farm_name: str = ""
    farmer_name: str = ""
    location: str = ""
    crop: str = ""
    crop_variety: str = ""
    growth_stage: str = ""
    soil_type: str = ""
    farm_area: float | None = None
    area_unit: str = "Acres"
    irrigation_method: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FarmProfile:
        valid_keys = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


# Farmer-friendly default options for dropdowns
COMMON_CROPS: list[str] = [
    "Rice (Paddy)",
    "Wheat",
    "Tomato",
    "Cotton",
    "Maize (Corn)",
    "Sugarcane",
    "Potato",
    "Onion",
    "Chilli",
    "Groundnut",
    "Soybean",
    "Other",
]

GROWTH_STAGES: list[str] = [
    "Sowing / Germination",
    "Vegetative Growth",
    "Flowering",
    "Fruiting / Pod Formation",
    "Harvesting / Mature",
]

SOIL_TYPES: list[str] = [
    "Loamy Soil",
    "Clay Soil",
    "Sandy Soil",
    "Black / Regur Soil",
    "Red Soil",
    "Alluvial Soil",
    "Silt Soil",
]

IRRIGATION_METHODS: list[str] = [
    "Drip Irrigation",
    "Sprinkler Irrigation",
    "Flood / Furrow Irrigation",
    "Rainfed / Manual",
]

AREA_UNITS: list[str] = ["Acres", "Hectares", "Bigha", "Guntha"]


def init_farm_profile() -> None:
    """Initialize farm_profile in Streamlit session state if missing."""
    if "farm_profile" not in st.session_state:
        st.session_state.farm_profile = FarmProfile().to_dict()


def get_farm_profile() -> FarmProfile:
    """Fetch the active FarmProfile from session state."""
    init_farm_profile()
    raw = st.session_state.farm_profile
    if isinstance(raw, FarmProfile):
        return raw
    if isinstance(raw, dict):
        return FarmProfile.from_dict(raw)
    return FarmProfile()


def save_farm_profile(profile: FarmProfile | dict[str, Any]) -> None:
    """Persist farm profile into session state."""
    if isinstance(profile, FarmProfile):
        st.session_state.farm_profile = profile.to_dict()
    elif isinstance(profile, dict):
        st.session_state.farm_profile = dict(profile)


def is_profile_configured(profile: FarmProfile | None = None) -> bool:
    """Check whether a meaningful farm profile exists."""
    p = profile if profile is not None else get_farm_profile()
    return bool(p.crop and p.crop.strip())


def validate_farm_profile(data: dict[str, Any] | FarmProfile) -> tuple[bool, dict[str, str]]:
    """Validate farm profile fields.

    Returns:
        (is_valid, errors_dict)
    """
    if isinstance(data, FarmProfile):
        d = data.to_dict()
    else:
        d = data

    errors: dict[str, str] = {}

    # Crop is required for personalization
    crop = d.get("crop", "")
    if not crop or not str(crop).strip():
        errors["crop"] = "Please select or specify a crop."

    # Farm area must be numeric and non-negative if provided
    area_val = d.get("farm_area")
    if area_val is not None and area_val != "":
        try:
            num = float(area_val)
            if num < 0:
                errors["farm_area"] = "Farm area cannot be negative."
        except (ValueError, TypeError):
            errors["farm_area"] = "Farm area must be a valid number."

    return (len(errors) == 0, errors)


def get_farm_context() -> dict[str, Any]:
    """Extract populated farm profile fields for downstream AI / services.

    Never fabricates missing information — only includes keys that are
    actually populated and non-empty.
    """
    profile = get_farm_profile()
    context: dict[str, Any] = {}

    if profile.crop and profile.crop.strip():
        context["crop"] = profile.crop.strip()
    if profile.crop_variety and profile.crop_variety.strip():
        context["crop_variety"] = profile.crop_variety.strip()
    if profile.growth_stage and profile.growth_stage.strip():
        context["growth_stage"] = profile.growth_stage.strip()
    if profile.soil_type and profile.soil_type.strip():
        context["soil_type"] = profile.soil_type.strip()
    if profile.irrigation_method and profile.irrigation_method.strip():
        context["irrigation_method"] = profile.irrigation_method.strip()
    if profile.location and profile.location.strip():
        context["location"] = profile.location.strip()
    if profile.farm_area is not None:
        context["farm_area"] = profile.farm_area
        context["area_unit"] = profile.area_unit
    if profile.farm_name and profile.farm_name.strip():
        context["farm_name"] = profile.farm_name.strip()
    if profile.farmer_name and profile.farmer_name.strip():
        context["farmer_name"] = profile.farmer_name.strip()

    return context
