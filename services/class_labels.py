"""Class label metadata loader and schema for KisanSense plant models.

Provides clean, configurable mapping between model output class indices
and farmer-friendly agronomic diagnoses, disease taxonomy, and advisory steps.
Supports models/plant_classes.json configuration.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import logging
import os
from pathlib import Path
import re
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_CLASSES_PATH = Path(__file__).resolve().parent.parent / "models" / "plant_classes.json"


@dataclass(frozen=True)
class ClassMetadata:
    """Structured agronomic diagnostic profile for a model class index."""

    index: int
    name: str
    crop: str
    disease: str
    category: str  # "fungal" | "bacterial" | "viral" | "abiotic_stress" | "healthy" | "unspecified"
    healthy: bool
    explanation: str
    recommended_action: str
    urgency: str  # "none" | "routine" | "moderate" | "immediate"

    def to_dict(self) -> dict[str, Any]:
        return {
            "index": self.index,
            "name": self.name,
            "crop": self.crop,
            "disease": self.disease,
            "category": self.category,
            "healthy": self.healthy,
            "explanation": self.explanation,
            "recommended_action": self.recommended_action,
            "urgency": self.urgency,
        }


def parse_raw_class_string(raw_name: str, index: int = 0) -> ClassMetadata:
    """Intelligently parse crop and condition from standard agricultural dataset naming conventions.

    Handles formats like:
      - 'Tomato___Early_blight'
      - 'Corn_(maize)___Common_rust_'
      - 'Pepper,_bell___Bacterial_spot'
      - 'Potato___Late_blight'
      - 'Class_0' or 'class_0'
    """
    clean = str(raw_name).strip()
    if not clean or clean.lower().startswith("class_") or clean.isdigit():
        idx_num = index if (not clean.isdigit()) else int(clean)
        return ClassMetadata(
            index=idx_num,
            name=f"Class_{idx_num}",
            crop="Crop",
            disease=f"Class {idx_num} Detection",
            category="unspecified",
            healthy=False,
            explanation=(
                f"Model classified this specimen as Class {idx_num}. "
                "Class labels can be configured in models/plant_classes.json."
            ),
            recommended_action="Inspect foliage carefully and consult local agricultural extension officers.",
            urgency="routine",
        )

    # Check for separator like '___', '__', or ' - '
    if "___" in clean:
        parts = clean.split("___", 1)
    elif " - " in clean:
        parts = clean.split(" - ", 1)
    elif "__" in clean:
        parts = clean.split("__", 1)
    else:
        parts = [clean, ""]

    raw_crop = parts[0].replace("_", " ").strip()
    # Clean crop formatting: 'Corn (maize)' -> 'Corn', 'Pepper, bell' -> 'Bell Pepper'
    raw_crop = re.sub(r"\([^)]*\)", "", raw_crop).strip()
    if "pepper" in raw_crop.lower() and "bell" in raw_crop.lower():
        crop_title = "Bell Pepper"
    else:
        crop_title = raw_crop.title() if raw_crop else "Crop"

    raw_disease = parts[1].replace("_", " ").strip() if len(parts) > 1 else ""
    disease_clean = raw_disease.title() if raw_disease else "Specimen"

    is_healthy = "healthy" in raw_disease.lower() or "healthy" in clean.lower()

    if is_healthy:
        category = "healthy"
        urgency = "none"
        explanation = (
            f"Foliage of {crop_title} appears vibrant and healthy with no prominent signs "
            "of pathogen lesions, blight, or nutrient deficiency."
        )
        action = "Maintain regular crop monitoring and standard irrigation schedules."
    else:
        # Determine pathology category
        lower_disease = raw_disease.lower()
        if "bacteria" in lower_disease or "canker" in lower_disease:
            category = "bacterial"
            urgency = "moderate"
            explanation = (
                f"Visual indicators consistent with bacterial infection ({disease_clean}) "
                f"observed on {crop_title} leaf tissue."
            )
            action = (
                "Avoid overhead irrigation, remove infected leaf debris, sanitize pruning tools, "
                "and consult agricultural specialists for approved copper-based bactericides if needed."
            )
        elif any(v in lower_disease for v in ["virus", "mosaic", "curl", "viroid"]):
            category = "viral"
            urgency = "immediate"
            explanation = (
                f"Foliar patterns indicate possible viral symptoms ({disease_clean}) on {crop_title}, "
                "often transmitted by insect vectors like whiteflies or aphids."
            )
            action = (
                "Isolate or cull severely stunted plants to prevent transmission, monitor and control vector insects, "
                "and verify with your local agricultural extension service."
            )
        elif "chlorosis" in lower_disease or "deficiency" in lower_disease or "stress" in lower_disease:
            category = "abiotic_stress"
            urgency = "routine"
            explanation = (
                f"Leaf discoloration suggests abiotic stress or nutrient imbalance ({disease_clean}) on {crop_title}."
            )
            action = "Check soil pH, root-zone moisture, and apply balanced micro-nutrients as recommended."
        else:
            category = "fungal"
            urgency = "immediate" if "late" in lower_disease or "wilt" in lower_disease else "moderate"
            explanation = (
                f"Symptoms characteristic of foliar fungal disease ({disease_clean}) detected on {crop_title} leaf."
            )
            action = (
                "Prune infected lower foliage to enhance canopy aeration, ensure leaves dry quickly, "
                "and seek extension guidance on registered bio-fungicides or protective sprays."
            )

    return ClassMetadata(
        index=index,
        name=clean,
        crop=crop_title,
        disease=disease_clean,
        category=category,
        healthy=is_healthy,
        explanation=explanation,
        recommended_action=action,
        urgency=urgency,
    )


_CACHED_MAPPING: dict[int, ClassMetadata] | None = None
_CACHED_PATH: str | None = None


def load_class_mapping(json_path: str | Path | None = None) -> dict[int, ClassMetadata]:
    """Load and cache the class index to ClassMetadata dictionary.

    Supports:
    1. A JSON list of class definition objects.
    2. A JSON dict mapping index strings to class definition objects.
    3. A JSON list of class name strings.
    4. A JSON dict with a "classes" key.
    """
    global _CACHED_MAPPING, _CACHED_PATH

    path_to_use = Path(json_path) if json_path else DEFAULT_CLASSES_PATH
    path_str = str(path_to_use.resolve())

    if _CACHED_MAPPING is not None and _CACHED_PATH == path_str:
        return _CACHED_MAPPING

    mapping: dict[int, ClassMetadata] = {}

    if path_to_use.is_file():
        try:
            with open(path_to_use, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict) and "classes" in data:
                data = data["classes"]

            if isinstance(data, list):
                for idx, item in enumerate(data):
                    if isinstance(item, dict):
                        item_idx = int(item.get("index", idx))
                        mapping[item_idx] = ClassMetadata(
                            index=item_idx,
                            name=str(item.get("name", f"Class_{item_idx}")),
                            crop=str(item.get("crop", "Crop")),
                            disease=str(item.get("disease", f"Class {item_idx}")),
                            category=str(item.get("category", "unspecified")),
                            healthy=bool(item.get("healthy", False)),
                            explanation=str(item.get("explanation", "")),
                            recommended_action=str(item.get("recommended_action", "")),
                            urgency=str(item.get("urgency", "routine")),
                        )
                    elif isinstance(item, str):
                        mapping[idx] = parse_raw_class_string(item, idx)
            elif isinstance(data, dict):
                for key_str, item in data.items():
                    try:
                        idx = int(key_str)
                    except ValueError:
                        continue
                    if isinstance(item, dict):
                        mapping[idx] = ClassMetadata(
                            index=idx,
                            name=str(item.get("name", f"Class_{idx}")),
                            crop=str(item.get("crop", "Crop")),
                            disease=str(item.get("disease", f"Class {idx}")),
                            category=str(item.get("category", "unspecified")),
                            healthy=bool(item.get("healthy", False)),
                            explanation=str(item.get("explanation", "")),
                            recommended_action=str(item.get("recommended_action", "")),
                            urgency=str(item.get("urgency", "routine")),
                        )
                    elif isinstance(item, str):
                        mapping[idx] = parse_raw_class_string(item, idx)
        except Exception as exc:
            logger.warning("Failed to load class mapping from %s: %s", path_to_use, exc)

    # Ensure at least 55 default fallback entries exist if mapping is empty or incomplete
    if not mapping:
        for i in range(55):
            mapping[i] = parse_raw_class_string(f"Class_{i}", i)

    _CACHED_MAPPING = mapping
    _CACHED_PATH = path_str
    return mapping


def get_class_metadata(index: int, json_path: str | Path | None = None) -> ClassMetadata:
    """Retrieve ClassMetadata for the specified class index."""
    mapping = load_class_mapping(json_path)
    if index in mapping:
        return mapping[index]
    return parse_raw_class_string(f"Class_{index}", index)
