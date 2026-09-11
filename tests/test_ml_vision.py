"""Unit and integration tests for KisanSense ML vision inference backend.

Validates:
- Model file discovery and architecture specs
- Class label mapping and parsing
- Preprocessing dimensions and pixel scaling
- Inference execution, output shape, and confidence calculation
- Automatic fallback when ML model is unavailable or encounters errors
- Safety warnings for low-confidence predictions
- VisionAnalysisResult backward compatibility contract
- Camera / Crop Scan UI result rendering
- Assistant context integration
"""

from __future__ import annotations

import io
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch

import numpy as np
from PIL import Image

from services.class_labels import (
    ClassMetadata,
    get_class_metadata,
    load_class_mapping,
    parse_raw_class_string,
)
from services.ml_vision_service import (
    DEFAULT_MODEL_PATH,
    EXPECTED_IMAGE_SIZE,
    EXPECTED_INPUT_SHAPE,
    NUM_OUTPUT_CLASSES,
    MLInferenceResult,
    get_model_status,
    preprocess_image_for_model,
    reset_model_cache,
    run_ml_inference,
    set_custom_predictor,
)
from services.vision_service import VisionAnalysisResult, analyze_plant_image


def _create_synthetic_leaf(
    width: int = 256,
    height: int = 256,
    color: tuple[int, int, int] = (40, 170, 40),
) -> Image.Image:
    """Create a synthetic green leaf image with texture variation to pass quality gate."""
    arr = np.zeros((height, width, 3), dtype=np.uint8)
    arr[:, :] = list(color)
    # Add natural variation so gradient variance passes sharpness gate
    arr[::4, ::4, 1] = min(255, int(color[1]) + 30)
    return Image.fromarray(arr)


def _image_to_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestMLVisionBackend(unittest.TestCase):
    """Test suite for ML vision backend and class mapping."""

    def setUp(self) -> None:
        reset_model_cache()

    def tearDown(self) -> None:
        reset_model_cache()

    # -------------------------------------------------------------------------
    # 1. Model Discovery & Status
    # -------------------------------------------------------------------------
    def test_model_file_discovery(self) -> None:
        """Verify plant_model_v5.keras is present in models/ with expected non-zero size."""
        self.assertTrue(DEFAULT_MODEL_PATH.is_file(), f"Model file missing at {DEFAULT_MODEL_PATH}")
        size_bytes = DEFAULT_MODEL_PATH.stat().st_size
        self.assertGreater(size_bytes, 20 * 1024 * 1024, "Model file size should be > 20MB")

    def test_model_status_reporting(self) -> None:
        """Verify get_model_status returns structured ModelStatus without raising."""
        status = get_model_status()
        self.assertIsNotNone(status)
        self.assertTrue(status.model_exists)
        self.assertEqual(status.num_classes, NUM_OUTPUT_CLASSES)

    # -------------------------------------------------------------------------
    # 2. Class Labels & Mapping Schema (VERIFIED TRAINING ORDER LOCK)
    # -------------------------------------------------------------------------
    def test_class_mapping_loading(self) -> None:
        """Verify 55 classes are loaded from models/plant_classes.json."""
        mapping = load_class_mapping()
        self.assertEqual(len(mapping), 55)
        for i in range(55):
            self.assertIn(i, mapping)
            meta = mapping[i]
            self.assertIsInstance(meta, ClassMetadata)
            self.assertEqual(meta.index, i)
            self.assertTrue(len(meta.crop) > 0)
            self.assertTrue(len(meta.disease) > 0)
            self.assertIn(meta.category, ["fungal", "bacterial", "viral", "abiotic_stress", "healthy", "unspecified"])
            self.assertIn(meta.urgency, ["none", "routine", "moderate", "immediate"])

    def test_verified_training_class_order_locking(self) -> None:
        """Lock the exact 55 training class ordering discovered in the original training codebase."""
        verified_55_classes = [
            "Apple___Apple_scab",
            "Apple___Black_rot",
            "Apple___Cedar_apple_rust",
            "Apple___healthy",
            "Blueberry___healthy",
            "Cherry_(including_sour)___Powdery_mildew",
            "Cherry_(including_sour)___healthy",
            "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot",
            "Corn_(maize)___Common_rust_",
            "Corn_(maize)___Northern_Leaf_Blight",
            "Corn_(maize)___healthy",
            "Grape___Black_rot",
            "Grape___Esca_(Black_Measles)",
            "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)",
            "Grape___healthy",
            "Orange___Citrus_Canker",
            "Orange___Haunglongbing_(Citrus_greening)",
            "Orange___Multiple_Diseases",
            "Orange___Nutrient_Deficiency",
            "Orange___healthy",
            "Peach___Bacterial_spot",
            "Peach___healthy",
            "Pepper,_bell___Bacterial_spot",
            "Pepper,_bell___healthy",
            "Potato___Early_blight",
            "Potato___Late_blight",
            "Potato___healthy",
            "Raspberry___healthy",
            "Soybean___Bacterial_Pustule",
            "Soybean___Brown_Spot",
            "Soybean___Crestamento",
            "Soybean___Ferrugen",
            "Soybean___Frogeye_Leaf_Spot",
            "Soybean___Mosaic_Virus",
            "Soybean___Powdery_Mildew",
            "Soybean___Rust",
            "Soybean___Septoria",
            "Soybean___Southern_Blight",
            "Soybean___Sudden_Death_Syndrome",
            "Soybean___Target_Leaf_Spot",
            "Soybean___Yellow_Mosaic",
            "Soybean___healthy",
            "Squash___Powdery_mildew",
            "Strawberry___Leaf_scorch",
            "Strawberry___healthy",
            "Tomato___Bacterial_spot",
            "Tomato___Early_blight",
            "Tomato___Late_blight",
            "Tomato___Leaf_Mold",
            "Tomato___Septoria_leaf_spot",
            "Tomato___Spider_mites Two-spotted_spider_mite",
            "Tomato___Target_Spot",
            "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
            "Tomato___Tomato_mosaic_virus",
            "Tomato___healthy",
        ]

        mapping = load_class_mapping()
        self.assertEqual(len(mapping), 55)

        for expected_idx, expected_name in enumerate(verified_55_classes):
            meta = get_class_metadata(expected_idx)
            self.assertEqual(
                meta.name,
                expected_name,
                f"Mismatch at index {expected_idx}: expected '{expected_name}', got '{meta.name}'",
            )
            self.assertEqual(meta.index, expected_idx)

    def test_prediction_mapping_pipeline(self) -> None:
        """Verify model predictions map correctly: index -> raw name -> crop -> disease -> category/healthy."""
        # Index 0: Apple Scab
        meta0 = get_class_metadata(0)
        self.assertEqual(meta0.name, "Apple___Apple_scab")
        self.assertEqual(meta0.crop, "Apple")
        self.assertEqual(meta0.disease, "Apple Scab")
        self.assertFalse(meta0.healthy)
        self.assertEqual(meta0.category, "fungal")

        # Index 15: Orange Citrus Canker
        meta15 = get_class_metadata(15)
        self.assertEqual(meta15.name, "Orange___Citrus_Canker")
        self.assertEqual(meta15.crop, "Orange")
        self.assertEqual(meta15.disease, "Citrus Canker")
        self.assertFalse(meta15.healthy)
        self.assertEqual(meta15.category, "bacterial")

        # Index 46: Tomato Early Blight
        meta46 = get_class_metadata(46)
        self.assertEqual(meta46.name, "Tomato___Early_blight")
        self.assertEqual(meta46.crop, "Tomato")
        self.assertEqual(meta46.disease, "Early Blight")
        self.assertFalse(meta46.healthy)
        self.assertEqual(meta46.category, "fungal")

        # Index 54: Tomato Healthy
        meta54 = get_class_metadata(54)
        self.assertEqual(meta54.name, "Tomato___healthy")
        self.assertEqual(meta54.crop, "Tomato")
        self.assertTrue(meta54.healthy)
        self.assertEqual(meta54.category, "healthy")

    def test_raw_class_string_parser(self) -> None:
        """Verify intelligent parsing of standard dataset class strings."""
        meta1 = parse_raw_class_string("Tomato___Early_blight", index=46)
        self.assertEqual(meta1.crop, "Tomato")
        self.assertEqual(meta1.disease, "Early Blight")
        self.assertFalse(meta1.healthy)
        self.assertEqual(meta1.category, "fungal")

        meta2 = parse_raw_class_string("Tomato___healthy", index=54)
        self.assertEqual(meta2.crop, "Tomato")
        self.assertTrue(meta2.healthy)
        self.assertEqual(meta2.category, "healthy")
        self.assertEqual(meta2.urgency, "none")

        meta3 = parse_raw_class_string("Pepper,_bell___Bacterial_spot", index=22)
        self.assertEqual(meta3.crop, "Bell Pepper")
        self.assertEqual(meta3.category, "bacterial")

        meta4 = parse_raw_class_string("Class_10", index=10)
        self.assertEqual(meta4.index, 10)
        self.assertEqual(meta4.crop, "Crop")

    # -------------------------------------------------------------------------
    # 3. Preprocessing Dimensions & Normalization
    # -------------------------------------------------------------------------
    def test_preprocessing_shape_and_range(self) -> None:
        """Verify input images are converted to (1, 224, 224, 3) float32 in [0.0, 255.0]."""
        img = _create_synthetic_leaf(400, 300, color=(120, 180, 90))
        tensor = preprocess_image_for_model(img)

        self.assertEqual(tensor.shape, EXPECTED_INPUT_SHAPE)
        self.assertEqual(tensor.dtype, np.float32)
        # Check scale remains [0, 255] because model has internal TrueDivide(127.5)
        self.assertGreaterEqual(float(tensor.min()), 0.0)
        self.assertLessEqual(float(tensor.max()), 255.0)

    def test_preprocessing_from_bytes(self) -> None:
        """Verify preprocessing works seamlessly on raw JPEG bytes."""
        img = _create_synthetic_leaf(200, 200)
        raw_bytes = _image_to_bytes(img)
        tensor = preprocess_image_for_model(raw_bytes)
        self.assertEqual(tensor.shape, (1, 224, 224, 3))

    # -------------------------------------------------------------------------
    # 4. ML Inference Execution & Top Probabilities
    # -------------------------------------------------------------------------
    def test_successful_ml_inference(self) -> None:
        """Verify successful ML inference produces high confidence and structured fields."""
        # Create a mock predictor returning class 46 (Tomato Early Blight) at 92%
        def mock_predictor(x: np.ndarray) -> np.ndarray:
            probs = np.full((1, NUM_OUTPUT_CLASSES), 0.08 / (NUM_OUTPUT_CLASSES - 1), dtype=np.float32)
            probs[0, 46] = 0.92  # Tomato Early Blight (Index 46 in verified order)
            return probs

        set_custom_predictor(mock_predictor)

        img = _create_synthetic_leaf()
        result = run_ml_inference(img, farm_context={"crop": "Tomato"})

        self.assertIsNotNone(result)
        self.assertTrue(result.success)
        self.assertEqual(result.predicted_class_index, 46)
        self.assertEqual(result.crop, "Tomato")
        self.assertEqual(result.disease, "Early Blight")
        self.assertAlmostEqual(result.confidence, 0.92, places=2)
        self.assertEqual(result.confidence_level, "high")
        self.assertEqual(result.inference_backend, "ml_keras")
        self.assertIn("Tomato___Early_blight", result.class_probabilities)

    def test_low_confidence_safety_warning(self) -> None:
        """Verify predictions below 0.60 trigger a conservative low-confidence warning."""
        # Mock predictor returning top class at only 42%
        def low_conf_predictor(x: np.ndarray) -> np.ndarray:
            probs = np.full((1, NUM_OUTPUT_CLASSES), 0.58 / (NUM_OUTPUT_CLASSES - 1), dtype=np.float32)
            probs[0, 1] = 0.42
            return probs

        set_custom_predictor(low_conf_predictor)

        img = _create_synthetic_leaf()
        result = run_ml_inference(img)

        self.assertIsNotNone(result)
        self.assertEqual(result.confidence_level, "low")
        self.assertLess(result.confidence, 0.60)
        has_low_conf_warn = any("AI confidence is low" in w for w in result.warnings)
        self.assertTrue(has_low_conf_warn, "Should include explicit low-confidence guidance warning")

    # -------------------------------------------------------------------------
    # 5. Fallback & Resiliency
    # -------------------------------------------------------------------------
    def test_fallback_when_model_fails_inference(self) -> None:
        """Verify analyze_plant_image falls back to deterministic vision when ML inference fails."""
        def crashing_predictor(x: np.ndarray) -> np.ndarray:
            raise RuntimeError("Simulated internal backend error")

        set_custom_predictor(crashing_predictor)

        # A synthetic foliage image passing quality gate
        leaf = _create_synthetic_leaf(256, 256, color=(20, 140, 30))
        result = analyze_plant_image(_image_to_bytes(leaf))

        # Must succeed via fallback engine without crashing
        self.assertTrue(result.success)
        self.assertEqual(result.inference_backend, "deterministic_fallback")
        self.assertEqual(result.model_source, "local_vision_engine")

    def test_corrupted_image_handling(self) -> None:
        """Verify invalid or corrupted image data is rejected gracefully by quality gate."""
        result = analyze_plant_image(b"this is not an image at all")
        self.assertFalse(result.success)
        self.assertEqual(result.disease_code, "CORRUPTED_FILE")

    def test_empty_image_handling(self) -> None:
        """Verify None image input returns NO_IMAGE gracefully."""
        result = analyze_plant_image(None)
        self.assertFalse(result.success)
        self.assertEqual(result.disease_code, "NO_IMAGE")

    # -------------------------------------------------------------------------
    # 6. Contract & Integration Preservation
    # -------------------------------------------------------------------------
    def test_vision_analysis_result_contract(self) -> None:
        """Verify VisionAnalysisResult retains all baseline attributes and includes additive ML attributes."""
        res = VisionAnalysisResult(
            success=True,
            is_plant=True,
            healthy=True,
            diagnosis="Healthy Foliage",
            disease_code="HEALTHY_FOLIAGE",
            crop="Wheat",
            category="healthy",
            confidence=0.88,
            confidence_level="high",
            explanation="Uniform vibrant green foliage.",
            recommended_action="Maintain routine care.",
            image_quality="good",
        )

        # Baseline attributes
        self.assertTrue(res.success)
        self.assertEqual(res.crop, "Wheat")
        self.assertEqual(res.model_source, "local_vision_engine")

        # Additive ML attributes
        self.assertEqual(res.inference_backend, "deterministic_fallback")
        self.assertEqual(res.model_name, "")
        self.assertEqual(res.model_confidence, 0.0)
        self.assertIsInstance(res.class_probabilities, dict)

    def test_ai_assistant_integration_with_ml_result(self) -> None:
        """Verify AI Assistant intelligence consumes ML vision result without error."""
        from services.ai_service import get_ai_response

        ml_vision_result = VisionAnalysisResult(
            success=True,
            is_plant=True,
            healthy=False,
            diagnosis="Tomato Early Blight",
            disease_code="TOMATO___EARLY_BLIGHT",
            crop="Tomato",
            category="fungal",
            confidence=0.91,
            confidence_level="high",
            explanation="Target-like brown lesions with chlorotic halos observed.",
            recommended_action="Prune affected lower leaves and improve ventilation.",
            image_quality="good",
            model_source="plant_model_v5",
            inference_backend="ml_keras",
            model_name="plant_model_v5",
            model_confidence=0.91,
            class_probabilities={"Tomato___Early_blight": 0.91},
        )

        context = {
            "crop": "Tomato",
            "farm_name": "Sunrise Farm",
            "vision_result": ml_vision_result,
        }

        # Ask question about disease
        response = get_ai_response(
            "What disease does my plant have?",
            context=context,
        )

        self.assertIsNotNone(response)
        self.assertIsInstance(response, str)
        # Should reference either the diagnosis or crop health
        self.assertTrue(
            "Early Blight" in response or "Tomato" in response or "Plant Health" in response
        )

    # -------------------------------------------------------------------------
    # 7. UI Rendering Regression Tests
    # -------------------------------------------------------------------------
    def test_result_card_html_rendering_no_code_blocks(self) -> None:
        """Verify _render_result_card produces pure HTML with zero code-block escapes.

        Regression test: Prevents CommonMark/Streamlit from interpreting 4-space
        indentations or blank lines as an indented code block (<pre><code>).
        """
        from views.farm import _render_result_card
        import markdown_it

        md = markdown_it.MarkdownIt()

        test_cases = [
            # Case 1: High confidence ML result
            VisionAnalysisResult(
                success=True,
                is_plant=True,
                healthy=False,
                diagnosis="Tomato Early Blight",
                disease_code="TOMATO_EARLY_BLIGHT",
                crop="Tomato",
                category="fungal",
                confidence=0.92,
                confidence_level="high",
                explanation="Dark water-soaked necrotic foliar lesions observed across crop leaves.",
                recommended_action="Isolate affected plants where practical, ensure canopy ventilation, avoid wetting leaves during watering, and consult your local agricultural expert.",
                image_quality="good",
                symptoms_detected=["dark_water_soaked_spots", "foliar_necrosis"],
                model_source="plant_model_v5",
                inference_backend="ml_keras",
            ),
            # Case 2: Low confidence ML result (triggers low_conf_banner)
            VisionAnalysisResult(
                success=True,
                is_plant=True,
                healthy=False,
                diagnosis="Tomato Late Blight",
                disease_code="TOMATO_LATE_BLIGHT",
                crop="Tomato",
                category="fungal",
                confidence=0.52,
                confidence_level="low",
                explanation="Irregular dark water-soaked patches expanding rapidly.",
                recommended_action="Improve air flow and remove heavily affected foliage.",
                image_quality="good",
                symptoms_detected=["water_soaked_patches"],
                model_source="plant_model_v5",
                inference_backend="ml_keras",
            ),
            # Case 3: Local Vision Engine fallback
            VisionAnalysisResult(
                success=True,
                is_plant=True,
                healthy=True,
                diagnosis="Healthy Foliage",
                disease_code="HEALTHY",
                crop="Tomato",
                category="healthy",
                confidence=0.88,
                confidence_level="high",
                explanation="Leaf lamina exhibits balanced chlorophyll pigmentation.",
                recommended_action="Maintain routine crop care and monitoring.",
                image_quality="good",
                model_source="deterministic_vision_engine",
                inference_backend="deterministic_fallback",
            ),
        ]

        for case in test_cases:
            captured_markdown: list[tuple[str, dict]] = []
            with patch("streamlit.markdown", side_effect=lambda content, **kwargs: captured_markdown.append((content, kwargs))):
                with patch("streamlit.button"):
                    with patch("streamlit.expander"):
                        _render_result_card(case, None)

            self.assertGreater(len(captured_markdown), 0)

            # Find the main diagnostic card call
            card_calls = [
                (content, kwargs)
                for content, kwargs in captured_markdown
                if "vision-card" in content and "vision-section-box" in content
            ]
            self.assertEqual(len(card_calls), 1)
            card_content, kwargs = card_calls[0]

            # 1. Must use unsafe_allow_html=True
            self.assertTrue(kwargs.get("unsafe_allow_html"), "Result card must specify unsafe_allow_html=True")

            # 2. Markdown parsing must not create code blocks
            tokens = md.parse(card_content)
            code_tokens = [t for t in tokens if t.type in ("code_block", "fence")]
            self.assertEqual(
                len(code_tokens),
                0,
                f"Result card markdown contains unwanted code block tokens: {code_tokens}",
            )

            # 3. Rendered HTML must not wrap card contents in <pre> or <code>
            rendered = md.render(card_content)
            self.assertNotIn("<pre>", rendered)
            self.assertNotIn("<code>", rendered)

            # 4. Critical agronomic UI sections must be present in the content
            self.assertIn(case.diagnosis, card_content)
            self.assertIn(case.crop, card_content)
            self.assertIn(case.explanation, card_content)
            self.assertIn(case.recommended_action, card_content)
            self.assertIn("What this means:", card_content)
            self.assertIn("What to do:", card_content)


if __name__ == "__main__":
    unittest.main()

