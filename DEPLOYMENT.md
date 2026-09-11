# KisanSense — Streamlit Cloud Deployment Guide

## Prerequisites

- GitHub repository: `1010slavin010/KisanSense-app-proto`
- Streamlit Community Cloud account linked to your GitHub

## Critical: Set Python 3.12

Streamlit Community Cloud does **NOT** read `runtime.txt` or `.python-version`.
You must configure the Python version via the dashboard:

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Find the **KisanSense** app
3. Click **Settings** → **Advanced settings**
4. Set **Python version** to **3.12**
5. Click **Save** and **Reboot**

> Without this step, TensorFlow will not install and the app will silently
> fall back to the deterministic Local Vision Engine instead of the
> AI Crop Model.

## How the ML Stack Works

```
requirements.txt
  └─ tensorflow-cpu>=2.16,<2.18  (installed only on Python < 3.13)
  └─ keras>=3.0,<4.0
  └─ h5py>=3.8,<4.0

models/
  ├─ plant_model_v5.keras         (24 MB, MobileNetV2, 55 classes)
  └─ plant_classes.json           (verified class-index mapping)

services/
  ├─ ml_vision_service.py         (Keras inference engine)
  ├─ class_labels.py              (55-class metadata)
  └─ vision_service.py            (orchestrator: ML primary → deterministic fallback)
```

### Inference Flow

1. User uploads a plant leaf image on the **Camera / Crop Scan** page
2. `vision_service.analyze_plant_image()` validates image quality
3. If quality passes, it calls `ml_vision_service.run_ml_inference()`
4. If the ML model is loaded and inference succeeds → **🤖 AI Crop Model** result
5. If the ML model is unavailable or fails → **⚙️ Local Vision Engine** (deterministic fallback)

### How to Verify AI Crop Model is Active

After deploying with Python 3.12:

1. Open the deployed app
2. Navigate to **Camera / Crop Scan**
3. Upload a clear plant leaf photo
4. The result card should display **🤖 AI Crop Model** as the inference source
5. If it shows **⚙️ Local Vision Engine**, check:
   - Python version is set to 3.12 in the dashboard
   - `requirements.txt` includes `tensorflow-cpu`
   - The app logs for TensorFlow/Keras import errors

## RAM Considerations

Streamlit Community Cloud provides **1 GB RAM** per app.

| Component | Estimated Memory |
|---|---|
| Streamlit + Python runtime | ~150 MB |
| TensorFlow CPU (loaded) | ~200–350 MB |
| Model in memory | ~25 MB |
| Image processing overhead | ~50 MB |
| **Total estimated** | **~425–575 MB** |

This should fit within the 1 GB limit under normal usage. If the app
crashes with resource errors, consider:

- Using `tflite-runtime` instead of full TensorFlow (requires model conversion)
- Deploying on a platform with more RAM (Railway, Render, etc.)

## Files Overview

| File | Purpose |
|---|---|
| `app.py` | Main Streamlit entry point |
| `requirements.txt` | Python dependencies with version pins |
| `.streamlit/config.toml` | Theme and server configuration |
| `models/plant_model_v5.keras` | Trained Keras 3 plant disease model (55 classes) |
| `models/plant_classes.json` | Verified class-index mapping |
| `services/ml_vision_service.py` | ML inference engine |
| `services/vision_service.py` | Vision orchestrator (ML → fallback) |
| `services/class_labels.py` | Class metadata and advisory text |
