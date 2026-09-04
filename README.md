# KisanSense — Phase 1

A farmer-friendly smart farming platform built with Python + Streamlit.
This is Phase 1: a polished Home dashboard, navigation shell, and an
on-page AI assistant, all running on mock data.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Then open the local URL Streamlit prints (usually http://localhost:8501).

## Project structure

```
KisanSense/
├── app.py                     # entry point: page config, CSS, routing
├── views/                     # one render() function per section
│   ├── home.py                # fully built: cards + assistant
│   ├── farm.py                # placeholder (Phase 2)
│   ├── irrigation.py          # placeholder (Phase 4)
│   ├── vision.py               # placeholder (Phase 6)
│   ├── assistant.py           # placeholder (Phase 5)
│   └── alerts.py              # placeholder (Phase 7)
├── components/                 # reusable UI pieces
│   ├── navbar.py
│   ├── cards.py
│   ├── chatbot.py
│   ├── status.py
│   └── placeholder.py
├── services/                   # business logic, no UI code
│   ├── sensor_service.py       # mock sensor data
│   ├── irrigation_service.py   # irrigation decision rule
│   └── ai_service.py           # mock assistant replies
├── utils/
│   ├── config.py                # constants & thresholds
│   ├── translations.py          # t(key) lookup, English only for now
│   └── helpers.py               # soil/temperature status + formatting
├── assets/
│   └── style.css                # design system
├── .streamlit/config.toml       # theme
├── requirements.txt
└── .gitignore
```

### One deviation from the original brief

The suggested layout put page files in a folder named `pages/`. Streamlit
auto-detects any folder called `pages/` next to `app.py` and builds its
own sidebar navigation from it, which would fight with the custom navbar
and session-state routing here. The folder is named `views/` instead —
same role, same file names, just renamed to avoid that collision.

## Phase 1 feature checklist

- [x] Home dashboard with soil moisture, temperature and irrigation cards
- [x] Deterministic irrigation rule based on soil moisture
- [x] Mock sensor data service, isolated behind `get_current_sensor_data()`
- [x] "Ask KisanSense" assistant on the Home page, with session-persisted
      chat history and a mock, clearly-labeled response service
- [x] Custom top navigation across 6 sections; Home is fully functional,
      the rest are intentional placeholders naming their planned phase
- [x] Design system distinct from default Streamlit styling
- [x] Responsive layout (Streamlit's columns stack on narrow screens)
- [x] Translation architecture (`t(key)`) used for Home/nav copy, English only

## Known limitations (intentional for Phase 1)

- Sensor data is simulated (`random.uniform`), generated once per browser
  session and cached in `session_state` so the dashboard doesn't visibly
  jump around — no ESP32/API integration yet.
- The assistant uses simple keyword matching, not a real AI model — see
  the docstring in `services/ai_service.py`.
- Only English strings are populated in `utils/translations.py`.
- Farm, Irrigation, Vision, Assistant and Alerts pages are placeholders.
- No database — nothing persists across a fresh browser session.

## How Phase 2 plugs in

Phase 2 (farm profile) mainly touches `views/farm.py` and would likely add
a `services/farm_service.py` alongside the existing services, following
the same pattern: pure functions returning structured data, no Streamlit
calls inside the service layer. `app.py`, the navbar, and the design
system don't need to change — `views/farm.py` already has a `render()`
placeholder to replace with the real implementation.
