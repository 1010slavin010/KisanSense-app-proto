"""ML Vision Service for KisanSense.

Provides edge-ready, offline machine learning inference for plant disease
classification using plant_model_v5.keras (Keras 3 / MobileNetV2 architecture).

Operates as the PRIMARY disease-classification engine when available,
with automatic fallback to the deterministic vision engine on any error,
missing dependency, or environment limitation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import io
import logging
import os
from pathlib import Path
import time
from typing import Any, Callable

import numpy as np
from PIL import Image

from services.class_labels import ClassMetadata, get_class_metadata, load_class_mapping

logger = logging.getLogger(__name__)

# Model Architecture Specifications (determined from plant_model_v5.keras inspection)
MODEL_FILENAME = "plant_model_v5.keras"
DEFAULT_MODEL_DIR = Path(__file__).resolve().parent.parent / "models"
DEFAULT_MODEL_PATH = DEFAULT_MODEL_DIR / MODEL_FILENAME

EXPECTED_INPUT_SHAPE = (1, 224, 224, 3)
EXPECTED_IMAGE_SIZE = (224, 224)
NUM_OUTPUT_CLASSES = 55
LOW_CONFIDENCE_THRESHOLD = 0.60
HIGH_CONFIDENCE_THRESHOLD = 0.80


@dataclass
class MLInferenceResult:
    """Structured result of ML crop disease classification inference."""

    success: bool
    predicted_class_index: int
    raw_class_name: str
    crop: str
    disease: str
    healthy: bool
    category: str  # "fungal" | "bacterial" | "viral" | "abiotic_stress" | "healthy" | "unspecified"
    confidence: float  # 0.0 to 1.0
    confidence_level: str  # "high" | "moderate" | "low"
    class_probabilities: dict[str, float] = field(default_factory=dict)
    all_probabilities: list[float] = field(default_factory=list)
    explanation: str = ""
    recommended_action: str = ""
    urgency: str = "routine"  # "none" | "routine" | "moderate" | "immediate"
    model_name: str = "plant_model_v5"
    model_version: str = "5.0"
    inference_backend: str = "ml_keras"
    inference_time_ms: float = 0.0
    warnings: list[str] = field(default_factory=list)
    error_message: str | None = None


@dataclass
class ModelStatus:
    """Diagnostic status of the ML inference backend."""

    available: bool
    model_path: str
    model_exists: bool
    backend: str
    reason: str
    input_shape: tuple[int | None, ...] | None = None
    num_classes: int = NUM_OUTPUT_CLASSES


# In-memory singleton cache for non-Streamlit environments and fast module access
_CACHED_MODEL_INSTANCE: Any | None = None
_MODEL_LOAD_ATTEMPTED: bool = False
_MODEL_LOAD_ERROR: str | None = None
_CUSTOM_PREDICTOR: Callable[[np.ndarray], np.ndarray] | None = None


def set_custom_predictor(predictor: Callable[[np.ndarray], np.ndarray] | None) -> None:
    """Inject a custom predictor function (primarily used for unit testing)."""
    global _CUSTOM_PREDICTOR
    _CUSTOM_PREDICTOR = predictor


def reset_model_cache() -> None:
    """Clear cached model instances to allow clean re-initialization."""
    global _CACHED_MODEL_INSTANCE, _MODEL_LOAD_ATTEMPTED, _MODEL_LOAD_ERROR, _CUSTOM_PREDICTOR
    _CACHED_MODEL_INSTANCE = None
    _MODEL_LOAD_ATTEMPTED = False
    _MODEL_LOAD_ERROR = None
    _CUSTOM_PREDICTOR = None


def preprocess_image_for_model(
    image_input: Image.Image | bytes | io.BytesIO,
    target_size: tuple[int, int] = EXPECTED_IMAGE_SIZE,
) -> np.ndarray:
    """Preprocess a plant image to match the exact input requirements of plant_model_v5.keras.

    Model Inspection Specification:
      - Input shape: [None, 224, 224, 3], float32.
      - Embedded layers: TrueDivide(127.5) -> Subtract(1.0).
      - Preprocessing contract: RGB float32 array in raw pixel scale [0.0, 255.0].

    Returns:
      NumPy array of shape (1, 224, 224, 3) with dtype float32.
    """
    if isinstance(image_input, (bytes, bytearray)):
        img = Image.open(io.BytesIO(image_input))
    elif isinstance(image_input, io.BytesIO):
        img = Image.open(image_input)
    elif isinstance(image_input, Image.Image):
        img = image_input
    elif hasattr(image_input, "getvalue"):
        img = Image.open(io.BytesIO(image_input.getvalue()))
    else:
        raise ValueError(f"Unsupported image input type: {type(image_input)}")

    # Ensure RGB color space (discards alpha channel or converts grayscale)
    if img.mode != "RGB":
        img = img.convert("RGB")

    # Resize to exact expected input dimensions
    if img.size != target_size:
        img = img.resize(target_size, Image.Resampling.BILINEAR)

    # Convert to float32 NumPy array with range [0.0, 255.0]
    arr = np.asarray(img, dtype=np.float32)

    # Add batch dimension: (224, 224, 3) -> (1, 224, 224, 3)
    if arr.ndim == 3:
        arr = np.expand_dims(arr, axis=0)

    return arr


def _load_keras_model_safely(model_path: Path) -> tuple[Any | None, str | None]:
    """Safely load plant_model_v5.keras using Keras 3 with defensive exception handling.

    Returns:
      (model_instance_or_none, error_message_or_none)
    """
    if not model_path.is_file():
        return None, f"Model file not found at {model_path}"

    try:
        # Check environment and configure backend if not explicitly set
        if "KERAS_BACKEND" not in os.environ:
            try:
                import tensorflow  # noqa: F401
                os.environ["KERAS_BACKEND"] = "tensorflow"
            except (ImportError, OSError):
                try:
                    import torch  # noqa: F401
                    os.environ["KERAS_BACKEND"] = "torch"
                except (ImportError, OSError):
                    pass

        import keras

        # Load Keras 3 model
        model = keras.models.load_model(str(model_path.resolve()), compile=False)
        return model, None
    except (ImportError, OSError, RuntimeError, Exception) as exc:
        err_msg = f"{type(exc).__name__}: {exc}"
        if "optree" in err_msg.lower():
            try:
                import optree  # noqa: F401
            except Exception as opt_err:
                err_msg = f"{err_msg} -> Underlying cause: {type(opt_err).__name__}: {opt_err}"
        logger.warning("Could not load Keras model from %s: %s", model_path, err_msg)
        return None, err_msg


def get_model(model_path: Path | None = None) -> Any | None:
    """Retrieve or lazily load the cached ML model instance.

    Uses Streamlit's @st.cache_resource when running inside Streamlit,
    and a resilient process-level singleton otherwise.
    """
    global _CACHED_MODEL_INSTANCE, _MODEL_LOAD_ATTEMPTED, _MODEL_LOAD_ERROR

    if _CUSTOM_PREDICTOR is not None:
        return _CUSTOM_PREDICTOR

    if _CACHED_MODEL_INSTANCE is not None:
        return _CACHED_MODEL_INSTANCE

    if _MODEL_LOAD_ATTEMPTED and _MODEL_LOAD_ERROR is not None:
        # Avoid repeatedly attempting to load a known-failed model in the same process
        return None

    path = model_path or DEFAULT_MODEL_PATH

    # Attempt Streamlit resource caching if Streamlit is active
    try:
        import streamlit as st
        if hasattr(st, "cache_resource"):
            @st.cache_resource(show_spinner=False)
            def _st_load(p_str: str) -> tuple[Any | None, str | None]:
                return _load_keras_model_safely(Path(p_str))

            loaded, err = _st_load(str(path))
            _MODEL_LOAD_ATTEMPTED = True
            _MODEL_LOAD_ERROR = err
            _CACHED_MODEL_INSTANCE = loaded
            return loaded
    except Exception:
        pass

    # Standard process-level load
    loaded, err = _load_keras_model_safely(path)
    _MODEL_LOAD_ATTEMPTED = True
    _MODEL_LOAD_ERROR = err
    _CACHED_MODEL_INSTANCE = loaded
    return loaded


def get_model_status(model_path: Path | None = None) -> ModelStatus:
    """Return an informative status report on ML model availability and backend readiness."""
    path = model_path or DEFAULT_MODEL_PATH
    exists = path.is_file()

    if _CUSTOM_PREDICTOR is not None:
        return ModelStatus(
            available=True,
            model_path=str(path),
            model_exists=exists,
            backend="custom_test_predictor",
            reason="Active test predictor configured.",
            input_shape=EXPECTED_INPUT_SHAPE,
            num_classes=NUM_OUTPUT_CLASSES,
        )

    model = get_model(path)
    if model is not None:
        input_shape = getattr(model, "input_shape", EXPECTED_INPUT_SHAPE)
        backend = os.environ.get("KERAS_BACKEND", "keras")
        return ModelStatus(
            available=True,
            model_path=str(path),
            model_exists=True,
            backend=f"keras_{backend}",
            reason="ML model is loaded and ready for inference.",
            input_shape=input_shape,
            num_classes=NUM_OUTPUT_CLASSES,
        )

    reason = _MODEL_LOAD_ERROR or "Model not loaded."
    if not exists:
        reason = f"Model file '{MODEL_FILENAME}' is missing from {path.parent}."
    elif _MODEL_LOAD_ERROR and ("optree" in _MODEL_LOAD_ERROR.lower() or "tensorflow" in _MODEL_LOAD_ERROR.lower()):
        import sys
        if sys.version_info >= (3, 13):
            py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            reason = (
                f"{reason} [Environment note: Current runtime is Python {py_ver}. "
                f"Production TensorFlow/Keras runtime requires Python <= 3.12, "
                f"as declared in requirements.txt ('tensorflow-cpu>=2.16; python_version < \"3.13\"')]."
            )

    return ModelStatus(
        available=False,
        model_path=str(path),
        model_exists=exists,
        backend="none",
        reason=reason,
        input_shape=None,
        num_classes=NUM_OUTPUT_CLASSES,
    )


def run_ml_inference(
    image_input: Image.Image | bytes | io.BytesIO,
    farm_context: dict[str, Any] | None = None,
    model_path: Path | None = None,
) -> MLInferenceResult | None:
    """Execute local ML crop disease classification inference on a preprocessed image.

    Args:
        image_input: Raw image bytes, PIL Image, or file stream.
        farm_context: Optional farm context dictionary (e.g. active crop).
        model_path: Optional path override for the .keras model file.

    Returns:
        MLInferenceResult if inference succeeded, or None if the model is unavailable or inference failed.
    """
    model = get_model(model_path)
    if model is None and _CUSTOM_PREDICTOR is None:
        return None

    ctx = farm_context or {}
    context_crop = (ctx.get("crop", "") or "").strip()

    t_start = time.perf_counter()

    # Step 1: Preprocess image
    try:
        input_tensor = preprocess_image_for_model(image_input)
    except Exception as exc:
        logger.warning("ML preprocessing failed: %s", exc)
        return None

    # Step 2: Execute Model Forward Pass
    try:
        if _CUSTOM_PREDICTOR is not None:
            raw_output = _CUSTOM_PREDICTOR(input_tensor)
        elif callable(model):
            # Keras 3 Functional models can be called directly
            raw_output = model(input_tensor, training=False)
        elif hasattr(model, "predict"):
            raw_output = model.predict(input_tensor, verbose=0)
        else:
            logger.warning("Loaded model object is not callable and lacks predict method.")
            return None

        # Convert output to 1D float32 NumPy array
        if hasattr(raw_output, "numpy"):
            probs = raw_output.numpy()
        elif hasattr(raw_output, "detach"):
            probs = raw_output.detach().cpu().numpy()
        else:
            probs = np.asarray(raw_output)

        if probs.ndim > 1:
            probs = probs[0]  # Take first batch item

        probs = probs.astype(np.float32)

    except Exception as exc:
        logger.warning("ML inference execution failed: %s", exc)
        return None

    t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0

    # Step 3: Validate output dimensions
    if len(probs) != NUM_OUTPUT_CLASSES:
        logger.warning(
            "Model output dimension mismatch: expected %d, received %d.",
            NUM_OUTPUT_CLASSES,
            len(probs),
        )
        return None

    # Step 4: Map probabilities and extract top predictions
    pred_idx = int(np.argmax(probs))
    conf = float(probs[pred_idx])

    # Extract Top-5 predictions
    top_indices = np.argsort(probs)[::-1][:5]
    top_probs_map: dict[str, float] = {}
    for idx in top_indices:
        meta = get_class_metadata(int(idx))
        top_probs_map[meta.name] = round(float(probs[idx]), 4)

    # Contextual check: if active crop matches a high-probability candidate within top 3
    if context_crop:
        for candidate_idx in top_indices[:3]:
            cand_meta = get_class_metadata(int(candidate_idx))
            cand_conf = float(probs[candidate_idx])
            # If user's crop matches candidate and candidate confidence is close (within 0.15)
            if (
                context_crop.lower() in cand_meta.crop.lower()
                and cand_meta.crop.lower() not in get_class_metadata(pred_idx).crop.lower()
                and (conf - cand_conf) < 0.15
                and cand_conf > 0.35
            ):
                pred_idx = int(candidate_idx)
                conf = cand_conf
                break

    meta = get_class_metadata(pred_idx)

    # Determine confidence level tier
    if conf >= HIGH_CONFIDENCE_THRESHOLD:
        conf_level = "high"
    elif conf >= LOW_CONFIDENCE_THRESHOLD:
        conf_level = "moderate"
    else:
        conf_level = "low"

    # Assemble safety warnings
    warnings: list[str] = [
        "AI Crop Model (MobileNetV2) inference assessment. Intended for agronomic decision support."
    ]
    if conf_level == "low":
        warnings.append(
            "AI confidence is low. Please take a clearer photo in good daylight or consult a local agriculture expert."
        )

    # Determine crop name
    final_crop = meta.crop
    if final_crop == "Crop" and context_crop:
        final_crop = context_crop

    return MLInferenceResult(
        success=True,
        predicted_class_index=pred_idx,
        raw_class_name=meta.name,
        crop=final_crop,
        disease=meta.disease,
        healthy=meta.healthy,
        category=meta.category,
        confidence=round(conf, 3),
        confidence_level=conf_level,
        class_probabilities=top_probs_map,
        all_probabilities=[round(float(p), 4) for p in probs],
        explanation=meta.explanation,
        recommended_action=meta.recommended_action,
        urgency=meta.urgency,
        model_name="plant_model_v5",
        model_version="5.0",
        inference_backend="ml_keras",
        inference_time_ms=round(t_elapsed_ms, 2),
        warnings=warnings,
        error_message=None,
    )
