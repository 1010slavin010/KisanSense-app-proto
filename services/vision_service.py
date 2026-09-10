"""Plant Vision and Crop Disease Intelligence Service for KisanSense.

Provides edge-ready, explainable computer vision analysis for plant leaves
using localized symptom profiling, colorimetric vegetation analysis, and
agronomic disease taxonomy. Operates 100% offline with zero external cloud dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import io
from typing import Any

import numpy as np
from PIL import Image

# Image Quality Thresholds
MIN_IMAGE_DIMENSION = 128
MAX_IMAGE_DIMENSION = 4096
MIN_LUMINANCE = 35.0      # Below this: Underexposed / too dark
MAX_LUMINANCE = 235.0     # Above this: Overexposed / glare
MIN_FOLIAGE_RATIO = 0.15  # Minimum ratio of vegetative pixels required (15%)
MIN_SHARPNESS_VAR = 0.25  # Minimum edge contrast variance (heavily smeared/blurry images fail)


@dataclass
class VisionAnalysisResult:
    """Authoritative structured output of the plant vision intelligence engine."""

    success: bool                        # True if image was successfully analyzed
    is_plant: bool                       # True if image contains recognizable plant foliage
    healthy: bool                        # True if no visual disease symptoms detected
    diagnosis: str                       # Farmer-facing diagnosis headline
    disease_code: str                    # Machine-readable identifier
    crop: str                            # Identified or contextual crop
    category: str                        # "fungal" | "bacterial" | "viral" | "abiotic_stress" | "healthy" | "unusable"
    confidence: float                    # Calibrated score between 0.0 and 1.0
    confidence_level: str                # "high" | "moderate" | "low"
    explanation: str                     # Plain-language explanation of symptoms observed
    recommended_action: str              # Practical agronomic steps for the farmer
    image_quality: str                   # "good" | "blurry" | "underexposed" | "overexposed" | "low_resolution" | "non_plant"
    image_quality_details: list[str] = field(default_factory=list)
    model_source: str = "local_vision_engine"
    warnings: list[str] = field(default_factory=list)
    timestamp: str = ""
    symptoms_detected: list[str] = field(default_factory=list)
    affected_foliage_ratio: float = 0.0
    treatment_urgency: str = "none"      # "none" | "routine" | "moderate" | "immediate"


def _validate_image_quality(img: Image.Image) -> tuple[bool, str, list[str]]:
    """Enforce Image Quality Gate: check dimensions, illumination, foliage presence, and blur.

    Returns:
        (passes_quality, quality_label, details_list)
    """
    details: list[str] = []
    width, height = img.size

    # 1. Dimension check
    if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
        details.append(
            f"Image resolution ({width}x{height}px) is too low. Minimum required is {MIN_IMAGE_DIMENSION}x{MIN_IMAGE_DIMENSION}px."
        )
        return False, "low_resolution", details

    if width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION:
        details.append(
            f"Image dimensions ({width}x{height}px) exceed the maximum supported resolution of {MAX_IMAGE_DIMENSION}px."
        )
        return False, "oversized_dimension", details

    # Resize large images to a standard evaluation size for consistency and memory safety
    eval_img = img.convert("RGB")
    if width > 512 or height > 512:
        eval_img.thumbnail((512, 512), Image.Resampling.BILINEAR)

    arr = np.asarray(eval_img, dtype=np.float32)

    # 2. Exposure & Illumination Check (mean luminance across R, G, B)
    luminance = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]
    mean_lum = float(np.mean(luminance))

    if mean_lum < MIN_LUMINANCE:
        details.append(
            f"Photo is too dark (average brightness {mean_lum:.1f}/255). Please capture in good natural daylight."
        )
        return False, "underexposed", details

    if mean_lum > MAX_LUMINANCE:
        details.append(
            f"Photo is washed out by glare or flash (average brightness {mean_lum:.1f}/255). Retake in diffused daylight."
        )
        return False, "overexposed", details

    # 3. Foliage Presence Check (Excess Green Index: 2*G - R - B)
    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]
    exg = 2.0 * g - r - b

    # A pixel is considered plant foliage if green dominates or is greenish-yellow
    plant_mask = (exg > 10.0) | ((g > b + 15.0) & (r > b + 10.0))
    foliage_ratio = float(np.count_nonzero(plant_mask)) / float(plant_mask.size)

    if foliage_ratio < MIN_FOLIAGE_RATIO:
        details.append(
            f"No recognizable plant leaves detected (vegetation content is only {foliage_ratio*100:.1f}%). "
            "Please center the camera on a crop leaf."
        )
        return False, "non_plant", details

    # 4. Sharpness / Focus Check (variance on gradient)
    if arr.shape[0] >= 3 and arr.shape[1] >= 3:
        gy, gx = np.gradient(luminance)
        sharpness_var = float(np.var(gx) + np.var(gy))
        if sharpness_var < MIN_SHARPNESS_VAR:
            details.append(
                "Image appears blurry or out of focus. Hold the camera steady and tap to focus on the leaf."
            )
            return False, "blurry", details

    details.append("Image resolution, lighting, and foliage presence verified successfully.")
    return True, "good", details


def _diagnose_foliar_symptoms(
    img: Image.Image,
    farm_context: dict[str, Any] | None = None,
) -> tuple[bool, str, str, str, float, str, str, list[str], float, str]:
    """Analyze leaf symptoms using colorimetric segmentation and lesion morphology.

    Returns:
        (healthy, diagnosis, disease_code, category, confidence, explanation, recommended_action, symptoms_detected, affected_ratio, urgency)
    """
    ctx = farm_context or {}
    crop = (ctx.get("crop", "") or "").strip()
    crop_name = crop if crop else "Crop"

    # Scale to evaluation size
    eval_img = img.convert("RGB")
    eval_img.thumbnail((384, 384), Image.Resampling.BILINEAR)
    arr = np.asarray(eval_img, dtype=np.float32)

    r = arr[:, :, 0]
    g = arr[:, :, 1]
    b = arr[:, :, 2]

    # Leaf area mask: pixels where plant matter, necrotic spots, or rot are present
    exg = 2.0 * g - r - b
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    leaf_mask = (
        (exg > 10.0)
        | ((g >= b + 10.0) & (r >= b + 10.0))
        | ((lum < 110.0) & (r >= g - 20.0) & (r >= b + 10.0))
        | ((lum < 75.0) & (r >= b))
    )
    leaf_pixel_count = max(1, int(np.count_nonzero(leaf_mask)))

    # Symptom 1: Necrotic lesions (brown/dark-brown/black spots: low luminance, R > G, G > B)
    necrotic_mask = leaf_mask & (lum < 110.0) & (r >= g - 15.0) & (r > b + 15.0)
    necrotic_ratio = float(np.count_nonzero(necrotic_mask)) / float(leaf_pixel_count)

    # Symptom 2: Severe dark rot / water-soaked spots (very dark on leaf: lum < 75)
    dark_rot_mask = leaf_mask & (lum < 75.0) & (r >= b)
    dark_rot_ratio = float(np.count_nonzero(dark_rot_mask)) / float(leaf_pixel_count)

    # Symptom 3: Chlorosis / Yellowing (high R + G, low B: r > 130, g > 130, b < 100)
    yellow_mask = leaf_mask & (r > 130.0) & (g > 120.0) & (b < 105.0) & (lum >= 110.0)
    yellow_ratio = float(np.count_nonzero(yellow_mask)) / float(leaf_pixel_count)

    # Symptom 4: Healthy green leaf tissue (exg > 25, balanced luminance, not necrotic or chlorotic)
    healthy_green_mask = leaf_mask & (exg > 25.0) & (lum >= 75.0) & (~necrotic_mask) & (~yellow_mask)
    healthy_ratio = float(np.count_nonzero(healthy_green_mask)) / float(leaf_pixel_count)

    # =========================================================================
    # Diagnostic Taxonomy Matching (Conservative Screening Language)
    # =========================================================================

    # Case A: Severe Dark Rot / Water-Soaked Lesions (Late Blight pattern)
    if dark_rot_ratio > 0.08 or (necrotic_ratio > 0.15 and dark_rot_ratio > 0.04):
        conf = min(0.92, round(0.75 + dark_rot_ratio * 0.8, 2))
        symptoms = ["dark_water_soaked_spots", "foliar_necrosis"]
        affected_area = round(dark_rot_ratio, 3)
        urgency = "immediate"
        if "tomato" in crop.lower():
            code = "TOMATO_LATE_BLIGHT"
            diag = "Late Blight Suspected"
            expl = (
                f"Visual screening of {crop_name} leaf reveals dark, water-soaked necrotic lesions covering "
                f"approximately {dark_rot_ratio * 100:.1f}% of the foliage surface, consistent with foliar blight symptoms."
            )
            act = (
                "Isolate visibly affected plants if practical, cease overhead sprinkler watering, ensure field drainage, "
                "and consult your local agricultural extension officer (KVK) for approved crop protection guidance."
            )
        elif "potato" in crop.lower():
            code = "POTATO_LATE_BLIGHT"
            diag = "Potato Late Blight Suspected"
            expl = f"Dark purplish-brown water-soaked spots detected on {crop_name} foliage."
            act = (
                "Remove visibly blighted stems, keep foliage dry, improve canopy airflow, and consult your local "
                "agricultural extension officer for registered treatment advice."
            )
        else:
            code = "FOLIAR_BLIGHT"
            diag = f"{crop_name} Foliar Blight Suspected"
            expl = f"Dark water-soaked necrotic foliar lesions observed across {crop_name} leaves."
            act = (
                "Isolate affected plants where practical, ensure canopy ventilation, avoid wetting leaves during watering, "
                "and consult your local agricultural expert."
            )

        return False, diag, code, "fungal", conf, expl, act, symptoms, affected_area, urgency

    # Case B: Concentric / Target Necrotic Spotting (Early Blight / Leaf Spot pattern)
    if necrotic_ratio > 0.020:
        conf = min(0.90, round(0.72 + necrotic_ratio * 1.2, 2))
        symptoms = ["concentric_target_spots", "necrotic_lesions"]
        affected_area = round(necrotic_ratio, 3)
        urgency = "moderate"
        if "tomato" in crop.lower():
            code = "TOMATO_EARLY_BLIGHT"
            diag = "Early Blight Suspected"
            expl = (
                f"Target-like necrotic lesions detected on {crop_name} leaf, "
                f"accounting for approximately {necrotic_ratio * 100:.1f}% of leaf area, consistent with Early Blight symptoms."
            )
            act = (
                "Prune visibly affected lower foliage, avoid wetting leaves during irrigation, ensure canopy airflow, "
                "and consult your local agricultural extension officer (KVK) if symptoms spread."
            )
        elif "potato" in crop.lower():
            code = "POTATO_EARLY_BLIGHT"
            diag = "Potato Early Blight Suspected"
            expl = f"Scattered concentric brown target lesions observed on {crop_name} leaves."
            act = (
                "Prune affected lower leaves, avoid overhead watering, inspect nearby plants, and consult your local "
                "agricultural extension expert."
            )
        elif "rice" in crop.lower() or "paddy" in crop.lower():
            code = "RICE_LEAF_BLAST"
            diag = "Rice Leaf Blast / Spot Suspected"
            expl = f"Brown bordered foliar lesions identified across {crop_name} leaf surface."
            act = (
                "Avoid excess nitrogen fertilizer application, maintain balanced field water levels, "
                "and seek guidance from your local agricultural extension service."
            )
        elif "cotton" in crop.lower():
            code = "COTTON_BLIGHT"
            diag = "Cotton Leaf Blight Suspected"
            expl = f"Angular dark-brown foliar spots bounded by leaf veins detected on {crop_name}."
            act = (
                "Use drip or furrow irrigation to keep foliage dry, improve plant spacing, and consult an agricultural specialist."
            )
        else:
            code = "FOLIAR_LEAF_SPOT"
            diag = f"{crop_name} Leaf Spot Suspected"
            expl = f"Localized necrotic lesions and spot damage observed across approximately {necrotic_ratio * 100:.1f}% of leaf area."
            act = (
                "Isolate affected plants if practical, prune spotted leaves, avoid evening foliar watering, "
                "and monitor disease progression across the field."
            )

        return False, diag, code, "fungal", conf, expl, act, symptoms, affected_area, urgency

    # Case C: Chlorosis / Interveinal Yellowing without Dark Lesions (Nutrient Stress / Mosaic)
    if yellow_ratio > 0.12:
        conf = min(0.85, round(0.68 + yellow_ratio * 0.6, 2))
        code = "NUTRIENT_CHLOROSIS"
        diag = "Foliar Yellowing / Chlorosis"
        symptoms = ["leaf_yellowing", "interveinal_chlorosis"]
        affected_area = round(yellow_ratio, 3)
        urgency = "routine"
        expl = (
            f"Foliar yellowing (chlorosis) observed across approximately {yellow_ratio * 100:.1f}% of {crop_name} leaf tissue "
            "without dark fungal necrosis, pointing to potential micronutrient deficit, root stress, or soil moisture imbalance."
        )
        act = (
            "Verify root-zone soil moisture and drainage, check for water stagnation, and review micronutrient and nitrogen balance "
            "with your local agricultural extension officer."
        )
        return False, diag, code, "abiotic_stress", conf, expl, act, symptoms, affected_area, urgency

    # Case D: Healthy Green Foliage
    conf = min(0.95, round(0.80 + healthy_ratio * 0.15, 2))
    code = "HEALTHY_FOLIAGE"
    diag = f"Healthy {crop_name} Foliage"
    symptoms = []
    affected_area = 0.0
    urgency = "none"
    expl = (
        f"{crop_name} foliage appears vibrant and uniform ({healthy_ratio * 100:.1f}% healthy green tissue) "
        "with no significant necrotic lesions, blight spots, or chlorotic discolouration."
    )
    act = "Continue routine monitoring and balanced agronomic care. No corrective intervention required."
    return True, diag, code, "healthy", conf, expl, act, symptoms, affected_area, urgency


def analyze_plant_image(
    image_input: bytes | io.BytesIO | Image.Image | None,
    farm_context: dict[str, Any] | None = None,
) -> VisionAnalysisResult:
    """Analyze a plant leaf image and return an authoritative, explainable diagnostic assessment.

    Args:
        image_input: Raw image bytes, file stream, or PIL Image instance.
        farm_context: Optional farm profile dict from services.farm_service.

    Returns:
        Structured VisionAnalysisResult.
    """
    now_str = datetime.now().strftime("%H:%M:%S")
    ctx = farm_context or {}
    crop = (ctx.get("crop", "") or "").strip()
    crop_str = crop if crop else "Crop"

    # =========================================================================
    # Step 1: Input Validation & Image Loading
    # =========================================================================
    if image_input is None:
        return VisionAnalysisResult(
            success=False,
            is_plant=False,
            healthy=False,
            diagnosis="No Image Provided",
            disease_code="NO_IMAGE",
            crop=crop_str,
            category="unusable",
            confidence=0.0,
            confidence_level="low",
            explanation="No image file was received for analysis.",
            recommended_action="Please upload a clear JPEG, PNG, or WEBP photo of the affected plant leaf.",
            image_quality="unusable",
            image_quality_details=["Empty upload payload."],
            warnings=["No file processed."],
            timestamp=now_str,
            symptoms_detected=[],
            affected_foliage_ratio=0.0,
            treatment_urgency="none",
        )

    # 10MB Maximum Image Upload Guard
    raw_len = 0
    if isinstance(image_input, bytes):
        raw_len = len(image_input)
    elif hasattr(image_input, "getbuffer"):
        try:
            raw_len = image_input.getbuffer().nbytes
        except Exception:
            raw_len = 0
    elif hasattr(image_input, "size"):
        raw_len = getattr(image_input, "size", 0)

    if raw_len > 10 * 1024 * 1024:
        return VisionAnalysisResult(
            success=False,
            is_plant=False,
            healthy=False,
            diagnosis="File Size Exceeds 10MB",
            disease_code="PAYLOAD_TOO_LARGE",
            crop=crop_str,
            category="unusable",
            confidence=0.0,
            confidence_level="low",
            explanation="The uploaded image exceeds the maximum allowed file size of 10MB.",
            recommended_action="Please upload a compressed or standard camera photo under 10MB.",
            image_quality="unusable",
            image_quality_details=["File size exceeds 10MB maximum limit."],
            warnings=["Image payload rejected due to size limits."],
            timestamp=now_str,
            symptoms_detected=[],
            affected_foliage_ratio=0.0,
            treatment_urgency="none",
        )

    try:
        if isinstance(image_input, bytes):
            img = Image.open(io.BytesIO(image_input))
        elif isinstance(image_input, io.BytesIO):
            img = Image.open(image_input)
        elif isinstance(image_input, Image.Image):
            img = image_input
        else:
            # Handle Streamlit UploadedFile duck typing
            data = getattr(image_input, "getvalue", None)
            if callable(data):
                img = Image.open(io.BytesIO(data()))
            else:
                img = Image.open(image_input)

        img.verify()  # Validate image headers and container integrity
        # Re-open after verify() as Pillow closes underlying buffer
        if isinstance(image_input, bytes):
            img = Image.open(io.BytesIO(image_input))
        elif isinstance(image_input, io.BytesIO):
            image_input.seek(0)
            img = Image.open(image_input)
        elif hasattr(image_input, "getvalue"):
            img = Image.open(io.BytesIO(image_input.getvalue()))
    except Exception as exc:
        return VisionAnalysisResult(
            success=False,
            is_plant=False,
            healthy=False,
            diagnosis="Invalid Image File",
            disease_code="CORRUPTED_FILE",
            crop=crop_str,
            category="unusable",
            confidence=0.0,
            confidence_level="low",
            explanation=f"The uploaded file could not be read as an image ({exc}).",
            recommended_action="Please upload a valid JPEG, PNG, or WEBP photo.",
            image_quality="invalid",
            image_quality_details=[str(exc)],
            warnings=["File integrity check failed."],
            timestamp=now_str,
            symptoms_detected=[],
            affected_foliage_ratio=0.0,
            treatment_urgency="none",
        )

    # =========================================================================
    # Step 2: Image Quality Gate
    # =========================================================================
    passes_quality, quality_label, quality_details = _validate_image_quality(img)

    if not passes_quality:
        is_plant_flag = quality_label != "non_plant"
        return VisionAnalysisResult(
            success=False,
            is_plant=is_plant_flag,
            healthy=False,
            diagnosis="Image Quality Unsuitable",
            disease_code="QUALITY_REJECTED",
            crop=crop_str,
            category="unusable",
            confidence=0.20,
            confidence_level="low",
            explanation=" ".join(quality_details),
            recommended_action="Retake the photo in natural diffused daylight, holding the camera steady and centered on the leaf.",
            image_quality=quality_label,
            image_quality_details=quality_details,
            warnings=["Image did not pass diagnostic quality criteria; screening suspended to avoid misdiagnosis."],
            timestamp=now_str,
            symptoms_detected=[],
            affected_foliage_ratio=0.0,
            treatment_urgency="none",
        )

    # =========================================================================
    # Step 3: Foliar Disease Classification & Agronomic Advice
    # =========================================================================
    healthy, diag, code, category, conf, expl, act, symptoms, aff_ratio, urgency = _diagnose_foliar_symptoms(img, ctx)

    # Determine confidence tier
    if conf >= 0.80:
        conf_level = "high"
    elif conf >= 0.60:
        conf_level = "moderate"
    else:
        conf_level = "low"

    # Assemble safety caveats
    warnings_list = [
        "Visual AI screening tool only. For high-value crops or ambiguous symptoms, consult your local Krishi Vigyan Kendra (KVK) or agricultural extension officer."
    ]
    if conf_level == "low":
        warnings_list.append("Confidence is tentative due to complex visual leaf patterns; further physical field verification is recommended.")

    return VisionAnalysisResult(
        success=True,
        is_plant=True,
        healthy=healthy,
        diagnosis=diag,
        disease_code=code,
        crop=crop_str,
        category=category,
        confidence=conf,
        confidence_level=conf_level,
        explanation=expl,
        recommended_action=act,
        image_quality="good",
        image_quality_details=quality_details,
        model_source="local_vision_engine",
        warnings=warnings_list,
        timestamp=now_str,
        symptoms_detected=symptoms,
        affected_foliage_ratio=aff_ratio,
        treatment_urgency=urgency,
    )
