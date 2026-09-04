"""App-wide constants for KisanSense (Phase 1).

Centralizing these avoids magic numbers scattered across pages,
components and services, and gives future phases one place to adjust
thresholds, branding or navigation.
"""

APP_NAME = "KisanSense"
APP_TAGLINE = "Smart farming, made simple."
PAGE_ICON = "🌾"

# Soil moisture thresholds (percent).
SOIL_MOISTURE_LOW = 30
SOIL_MOISTURE_HIGH = 60

# Comfortable temperature range for most crops (Celsius).
TEMP_NORMAL_MIN = 15
TEMP_NORMAL_MAX = 35

NAV_ITEMS = [
    ("home", "Home"),
    ("farm", "Farm"),
    ("irrigation", "Irrigation"),
    ("vision", "Vision"),
    ("assistant", "Assistant"),
    ("alerts", "Alerts"),
]
