# 🌱 KisanSense — AI-Powered Smart Farming Assistant

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.30+-FF4B4B.svg)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**KisanSense** is an end-to-end, farmer-centric decision-support platform designed for Smart India Hackathon (SIH) and real-world agricultural operations. It unifies low-power IoT telemetry (ESP32-ready), deterministic foliar vision intelligence, microclimate weather modeling, and a grounded advisory chatbot to empower smallholder and commercial farmers with actionable field intelligence.

---

## 🏗️ System Architecture

```
                    ┌─────────────────────────────────┐
                    │       ESP32 Microcontroller     │
                    │   DHT22 · Capacitive Soil · RSSI│
                    └────────────────┬────────────────┘
                                     │ Wi-Fi / HTTP POST
                                     ▼
                    ┌─────────────────────────────────┐
                    │      Telemetry Server / Ingest  │
                    │      Header Auth · Rate Limiter │
                    └────────────────┬────────────────┘
                                     │
                                     ▼
                    ┌─────────────────────────────────┐
                    │   Sensor Service / Hardware     │
                    │   Safe Fallback · Stale Check   │
                    └────────────────┬────────────────┘
                                     │
             ┌───────────────────────┴───────────────────────┐
             ▼                                               ▼
┌───────────────────────────────┐               ┌───────────────────────────────┐
│     Farm Intelligence         │               │     Plant Vision Screening    │
│  Moisture · Temp · Humidity   │               │   Quality Gate · Exposure     │
│  Weather Advisories & Trends  │               │   Color Histogram · Foliage   │
└───────────────┬───────────────┘               └───────────────┬───────────────┘
                │                                               │
                └───────────────────────┬───────────────────────┘
                                        ▼
                    ┌────────────────────────────────────────┐
                    │   Unified Farm Advisory Engine         │
                    │   Alerts · Timeline · Action Guidance  │
                    └───────────────────┬────────────────────┘
                                        │
           ┌────────────────────────────┼────────────────────────────┐
           ▼                            ▼                            ▼
   ┌───────────────┐            ┌───────────────┐            ┌───────────────┐
   │   Dashboard   │            │   Grounded    │            │ Centralized   │
   │  & Analytics  │            │ Farm Chatbot  │            │ Alert System  │
   └───────────────┘            └───────────────┘            └───────────────┘
```

---

## ✨ Core Features & Capabilities

### 1. Unified Home Dashboard
- **Instant Status Indicator**: Live evaluation categorizing field state into `HEALTHY`, `NEEDS ATTENTION`, or `CRITICAL`.
- **Key Metrics Grid**: Live soil moisture, canopy temperature, ambient humidity, and node status.
- **Unified Advisory Card**: High-confidence summary explaining *what* is happening, *why*, and *what to do next*.
- **Quick Action Bar**: One-click navigation to crop scanning, irrigation details, diagnostics, alerts, and AI consultation.

### 2. Advanced Irrigation Intelligence
- **Failsafe Decision Rules**: Conservative irrigation threshold triggers (`WATER NOW`, `MONITOR`, `NO WATER NEEDED`).
- **Hardware Safety Interlocks**: Hard safety gate—if a sensor is `OFFLINE`, `FAULTED`, or `STALE`, irrigation commands are strictly locked out (`FAIL-SAFE LOCKED`). Plant vision or external factors never bypass hardware safety.
- **Water Conservation Metrics**: Computes estimated water savings and evaporation efficiency.

### 3. Edge-Ready Telemetry & Diagnostics
- **Dual Telemetry Modes**: Instant switching between simulated testing conditions and live REST/ESP32 ingestion.
- **Device Health Monitoring**: Real-time evaluation of Node connection state, battery voltage ($V$), Wi-Fi signal ($RSSI$), reading age, and diagnostic error codes.
- **Troubleshooting Knowledgebase**: Actionable step-by-step resolution guides for physical field issues.

### 4. Plant Vision Screening (Deterministic & 100% Offline)
- **Zero Cloud Dependency**: Runs entirely in-memory using standard Pillow/NumPy; no external API latency, token costs, or data privacy risks.
- **Multi-Stage Quality Gate**: Automatically rejects corrupted, underexposed ($<25$ mean brightness), overexposed ($>230$), low-resolution, or non-foliage images before screening.
- **Phenotype & Foliar Analysis**: Identifies early indicators of Early Blight (*Alternaria solani*), Late Blight (*Phytophthora infestans*), Chlorosis/Nutrient deficiencies, and foliar stress with affected ratio percentages.

### 5. Weather Intelligence & Microclimate Modeling
- **Provider Abstraction**: Extensible interface supporting both localized simulated microclimates and third-party API providers.
- **Agronomic Cross-Referencing**: Synthesizes rain probability, dew point, wind speed, and humidity with field sensors to warn against fungal spread or pesticide drift.

### 6. Centralized Alerting & Event Timeline
- **Unified Alert Bus**: Prioritizes alerts (`CRITICAL`, `ALERT`, `WARNING`, `INFO`, `GOOD`) across soil moisture, extreme temperature, device health, and weather risks.
- **Session Event Log**: Tracks sensor recovery, irrigation recommendations, and plant scans in an intuitive chronological audit trail.

### 7. Grounded Agricultural Assistant ("Ask KisanSense")
- **Grounded Conversational AI**: Strictly conditioned on active farm profile data, live telemetry, weather status, foliar scans, and system alerts.
- **Zero Fabrication**: If telemetry, weather, or crop scans are unavailable, the assistant transparently informs the farmer rather than halluncinating figures.

### 8. Native Multilingual Support
- Fully localized across 4 Indian languages:
  - 🇬🇧 English (`en`)
  - 🇮🇳 हिन्दी (Hindi, `hi`)
  - 🇮🇳 தமிழ் (Tamil, `ta`)
  - 🇮🇳 ಕನ್ನಡ (Kannada, `kn`)

---

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.10, 3.11, or 3.12+
- Git

### Quickstart

1. **Clone the repository**:
   ```bash
   git clone https://github.com/1010slavin010/KisanSense-app-proto.git
   cd KisanSense-app-proto
   ```

2. **Create and activate a virtual environment**:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Launch the application**:
   ```bash
   streamlit run app.py
   ```
   Open `http://localhost:8501` in your browser.

---

## 🧪 Simulation Scenarios (SIH Demo Mode)

To facilitate live demonstration and grading without requiring live field hardware, KisanSense includes an interactive scenario selector in the sidebar:

| Condition | Soil Moisture | Temperature | Humidity | System Behavior / Advisory |
|---|---|---|---|---|
| **NORMAL** | 45% (Optimal) | 27°C (Mild) | 65% | Normal operations; balanced growth advisory. |
| **DRY** | 18% (Low) | 32°C (Warm) | 40% | `WATER NOW` recommended; drought advisory triggered. |
| **WET** | 82% (Saturated) | 22°C (Cool) | 88% | `NO WATER NEEDED`; waterlogging & root aeration risk. |
| **HOT** | 35% (Adequate) | 41°C (Extreme) | 30% | Heat stress advisory; recommend evening/morning irrigation. |
| **WATERLOGGING** | 90% (Flooded) | 24°C | 95% | Critical drainage alert; disease incubation risk. |
| **SENSOR_OFFLINE**| N/A | N/A | N/A | Hardware fail-safe active; pump controls locked. |
| **HEAT_DROUGHT** | 14% (Severe) | 42°C (Extreme) | 25% | Compound stress alert; emergency crop hydration guidance. |
| **HUMID_HEAT** | 50% (Moist) | 36°C (Hot) | 90% | High fungal incubation risk; foliar inspection advised. |

---

## 📡 Future ESP32 Hardware Integration

KisanSense is engineered to transition seamlessly from simulation to live hardware without code modifications:

1. **Hardware Configuration**:
   - ESP32 microcontroller with Wi-Fi capability.
   - DHT22 (Digital Ambient Temperature & Humidity).
   - Capacitive Soil Moisture Sensor v1.2 (Corrosion resistant).
   - Battery voltage divider on ADC pin 34.

2. **Ingestion Endpoint**:
   - ESP32 transmits JSON payloads via HTTP POST to the backend ingest server:
   ```json
   {
     "device_id": "KS-NODE-01",
     "api_key": "YOUR_SECRET_SENSOR_KEY",
     "soil_moisture": 34.5,
     "temperature": 28.2,
     "humidity": 68.0,
     "battery_v": 3.92,
     "rssi": -65
   }
   ```
3. **Environment & Secrets**:
   - Store sensitive keys in `.streamlit/secrets.toml` or OS environment variables:
     ```toml
     SENSOR_API_KEY = "your-secure-token-here"
     TELEMETRY_ENDPOINT = "http://192.168.1.100:8000/telemetry"
     ```

---

## 🛡️ Agronomic Safety & Responsible AI Disclaimer

> [!IMPORTANT]
> **Decision Support Only**: KisanSense is an assistive decision-support prototype. It does **NOT** substitute for professional agronomic consulting, soil laboratory testing, or certified phytopathological examination.
> 
> - **No Chemical Prescriptions**: KisanSense adheres to strict safety protocols and **never** recommends specific pesticide brand dosages or chemical treatments.
> - **Screening, Not Clinical Diagnosis**: Computer vision findings denote preliminary screening indicators. For suspected disease outbreaks, physical inspection and consultation with your local Krishi Vigyan Kendra (KVK) or agricultural extension officer is strongly recommended.
> - **Simulation Notice**: When running under simulated conditions, all sensor, weather, and battery metrics represent synthetic models for demonstration purposes.

---

## 👥 Authors & Acknowledgments

- Developed for the **Smart India Hackathon (SIH)**.
- Designed with high-contrast, accessible, and responsive Streamlit UI components tailored for Indian farmers.
