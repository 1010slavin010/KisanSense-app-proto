"""App-wide constants for KisanSense (Phase 1).

Centralizing these avoids magic numbers scattered across pages,
components and services, and gives future phases one place to adjust
thresholds, branding or navigation.
"""

import os

APP_NAME = "KisanSense"
APP_TAGLINE = "Smart farming, made simple."
PAGE_ICON = "static/favicon.png"

# Production base URL for canonical tags, sitemaps, Open Graph
KISANSENSE_BASE_URL = os.getenv("KISANSENSE_BASE_URL", "https://kisansense-app-proto.streamlit.app").rstrip("/")

# Soil moisture thresholds (percent).
SOIL_MOISTURE_LOW = 30
SOIL_MOISTURE_HIGH = 60

# Comfortable temperature range for most crops (Celsius).
TEMP_NORMAL_MIN = 15
TEMP_NORMAL_MAX = 35

NAV_ITEMS = [
    ("home", "Home"),
    ("farm", "Farm"),
    ("weather", "Weather"),
    ("irrigation", "Irrigation"),
    ("vision", "Vision"),
    ("assistant", "Assistant"),
    ("alerts", "Alerts"),
    ("devices", "Devices"),
    ("analytics", "Analytics"),
]

