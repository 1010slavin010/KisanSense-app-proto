"""Weather and Climate service for KisanSense.

Provides structured, deterministic weather snapshots and short-term forecasts
for agricultural decision support. Operates with an authoritative, offline-capable
demo simulator by default, ensuring 100% reliable local execution without mandatory
external API keys or cloud dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import hashlib
from typing import Any


@dataclass
class WeatherForecastDay:
    """Represents a discrete daily forecast for agricultural planning."""

    day_label: str  # "Today", "Tomorrow", "Day 3", etc.
    temp_min: float  # Celsius
    temp_max: float  # Celsius
    condition: str  # "Sunny", "Partly Cloudy", "Showers", "Thunderstorm", etc.
    icon: str  # "☀️", "🌤", "🌦", "🌧", "⛈"
    precipitation_probability: int  # 0 to 100 (%)
    precipitation_amount_mm: float  # mm
    humidity: float  # %
    wind_speed_kmh: float  # km/h

    @property
    def date_str(self) -> str:
        return self.day_label

    @property
    def temp_min_c(self) -> float:
        return self.temp_min

    @property
    def temp_max_c(self) -> float:
        return self.temp_max

    @property
    def rain_prob(self) -> int:
        return self.precipitation_probability

    @property
    def precipitation_mm(self) -> float:
        return self.precipitation_amount_mm

    @property
    def agrarian_advisory(self) -> str:
        if self.precipitation_probability >= 60:
            return "Soil moisture recharge expected — hold irrigation."
        elif self.precipitation_probability >= 30:
            return "Scattered light showers possible — monitor field."
        elif self.temp_max >= 35.0:
            return "High heat conditions — watch for midday crop stress."
        elif self.wind_speed_kmh <= 15.0:
            return "Calm winds — favorable window for foliar spraying."
        return "Stable conditions for normal field operations."

    def to_dict(self) -> dict[str, Any]:
        return {
            "day_label": self.day_label,
            "temp_min": self.temp_min,
            "temp_max": self.temp_max,
            "condition": self.condition,
            "icon": self.icon,
            "rain_prob": self.rain_prob,
            "precipitation_mm": self.precipitation_mm,
            "humidity": self.humidity,
            "wind_speed_kmh": self.wind_speed_kmh,
            "agrarian_advisory": self.agrarian_advisory,
        }


@dataclass
class WeatherSnapshot:
    """Authoritative structured output of current weather and short-term forecast."""

    location: str
    timestamp: str
    temperature: float  # Celsius
    feels_like: float  # Celsius
    humidity: float  # %
    precipitation_probability: int  # 0 to 100 (%)
    precipitation_amount_mm: float  # mm
    wind_speed_kmh: float  # km/h
    wind_direction: str  # e.g. "NW", "SE", "SW"
    weather_condition: str  # e.g. "Partly Cloudy", "Light Rain"
    condition_icon: str  # e.g. "🌤", "🌧", "☀️"
    forecast_summary: str  # Plain-language forecast description
    forecast_days: list[WeatherForecastDay] = field(default_factory=list)
    is_demo: bool = True
    source: str = "demo_weather_simulator"
    is_available: bool = True
    error_message: str = ""

    @property
    def temperature_c(self) -> float:
        return self.temperature

    @property
    def condition(self) -> str:
        return self.weather_condition

    @property
    def rain_probability(self) -> int:
        return self.precipitation_probability

    @property
    def precipitation_mm(self) -> float:
        return self.precipitation_amount_mm

    @property
    def evapotranspiration_mm(self) -> float:
        t = self.temperature
        h = max(10.0, self.humidity)
        w = self.wind_speed_kmh
        diff = max(1.0, t - 15.0)
        et0 = max(1.5, (0.0023 * (t + 17.8) * (diff ** 0.5) * (100.0 - h) / 100.0 * 12.0) + (w * 0.05))
        return round(et0, 1)

    @property
    def solar_irradiance_w_m2(self) -> float:
        cond_u = self.weather_condition.upper()
        if "SUNNY" in cond_u or "CLEAR" in cond_u:
            return 750.0
        elif "RAIN" in cond_u or "THUNDER" in cond_u:
            return 180.0
        elif "OVERCAST" in cond_u:
            return 320.0
        return 540.0

    @property
    def forecast(self) -> list[WeatherForecastDay]:
        return self.forecast_days

    def to_dict(self) -> dict[str, Any]:
        return {
            "location": self.location,
            "timestamp": self.timestamp,
            "temperature_c": self.temperature,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "rain_probability": self.precipitation_probability,
            "precipitation_mm": self.precipitation_amount_mm,
            "wind_speed_kmh": self.wind_speed_kmh,
            "condition": self.weather_condition,
            "evapotranspiration_mm": self.evapotranspiration_mm,
            "solar_irradiance_w_m2": self.solar_irradiance_w_m2,
            "forecast": [f.to_dict() for f in self.forecast_days],
            "is_demo": self.is_demo,
            "source": self.source,
        }


def _generate_deterministic_forecast(
    base_temp: float,
    base_humidity: float,
    base_rain_prob: int,
    base_rain_mm: float,
    base_wind: float,
    condition: str,
    icon: str,
) -> list[WeatherForecastDay]:
    """Build a realistic, deterministic 3-day forecast sequence."""
    day1 = WeatherForecastDay(
        day_label="Today",
        temp_min=round(base_temp - 5.0, 1),
        temp_max=round(base_temp + 3.0, 1),
        condition=condition,
        icon=icon,
        precipitation_probability=base_rain_prob,
        precipitation_amount_mm=base_rain_mm,
        humidity=base_humidity,
        wind_speed_kmh=base_wind,
    )

    # Tomorrow
    t2_prob = min(95, max(5, int(base_rain_prob * 1.2 if base_rain_prob > 30 else base_rain_prob + 10)))
    t2_icon = "🌧" if t2_prob > 60 else ("🌦" if t2_prob > 30 else "🌤")
    t2_cond = "Rain Showers" if t2_prob > 60 else ("Scattered Clouds" if t2_prob > 30 else "Sunny")
    day2 = WeatherForecastDay(
        day_label="Tomorrow",
        temp_min=round(base_temp - 6.0, 1),
        temp_max=round(base_temp + 2.0, 1),
        condition=t2_cond,
        icon=t2_icon,
        precipitation_probability=t2_prob,
        precipitation_amount_mm=round(base_rain_mm * 1.5 if t2_prob > 50 else 0.0, 1),
        humidity=round(min(98.0, base_humidity + 5.0), 1),
        wind_speed_kmh=round(base_wind + 2.0, 1),
    )

    # Day 3
    t3_prob = max(10, int(t2_prob * 0.75))
    t3_icon = "🌦" if t3_prob > 40 else "🌤"
    t3_cond = "Passing Clouds" if t3_prob > 30 else "Clear Skies"
    day3 = WeatherForecastDay(
        day_label="Day 3",
        temp_min=round(base_temp - 4.0, 1),
        temp_max=round(base_temp + 4.0, 1),
        condition=t3_cond,
        icon=t3_icon,
        precipitation_probability=t3_prob,
        precipitation_amount_mm=round(base_rain_mm * 0.4 if t3_prob > 40 else 0.0, 1),
        humidity=round(max(35.0, base_humidity - 8.0), 1),
        wind_speed_kmh=round(max(6.0, base_wind - 3.0), 1),
    )

    return [day1, day2, day3]


def get_weather_snapshot(
    location: str | None = None,
    condition_hint: str | None = None,
) -> WeatherSnapshot:
    """Retrieve weather data with deterministic agrarian simulation fallback.

    Args:
        location: Farm location string (e.g. "Nashik, Maharashtra").
        condition_hint: Optional simulation condition hint (e.g. "HOT", "WET", "DRY").

    Returns:
        Structured WeatherSnapshot with current conditions and 3-day forecast.
    """
    now_str = datetime.now().strftime("%I:%M %p")
    loc_clean = (location or "").strip()
    loc_display = loc_clean if loc_clean else "Mandya, Karnataka"

    # Location modulation
    temp_offset = 0.0
    loc_lower = loc_display.lower()
    if any(h in loc_lower for h in ("shimla", "kashmir", "hill", "ooty", "manali")):
        temp_offset = -9.0
    elif any(h in loc_lower for h in ("rajasthan", "thar", "desert")):
        temp_offset = +4.0
    elif "punjab" in loc_lower:
        temp_offset = +1.0

    # Base profile modulation according to condition_hint or location hash
    hint = (condition_hint or "").upper()

    if "HUMID" in hint:
        temp = 32.5 + temp_offset
        feels = 36.0 + temp_offset
        hum = 82.0
        rain_prob = 45
        rain_mm = 4.5
        wind = 9.0
        cond = "Humid & Overcast"
        icon = "🌦"
        summary = "Warm, high-humidity canopy conditions with intermittent light drizzle."
    elif "WET" in hint or "WATERLOGGING" in hint:
        temp = 24.5 + temp_offset
        feels = 25.0 + temp_offset
        hum = 88.0
        rain_prob = 80
        rain_mm = 24.0
        wind = 18.0
        cond = "Heavy Rain"
        icon = "🌧"
        summary = "Persistent rain showers with elevated atmospheric moisture."
    elif "DRY" in hint:
        temp = 31.0 + temp_offset
        feels = 32.0 + temp_offset
        hum = 38.0
        rain_prob = 15
        rain_mm = 0.0
        wind = 12.0
        cond = "Clear & Dry"
        icon = "🌤"
        summary = "Mild dry conditions with minimal cloud cover. No rainfall expected soon."
    elif "HOT" in hint or "HEAT" in hint:
        temp = 36.5 + temp_offset
        feels = 39.0 + temp_offset
        hum = 32.0
        rain_prob = 10
        rain_mm = 0.0
        wind = 14.0
        cond = "Hot & Sunny"
        icon = "☀️"
        summary = "Dry heatwave conditions with clear skies. Elevated crop evapotranspiration."
    else:
        # Default normal conditions: stable, comfortable agrarian climate
        temp = 27.0 + temp_offset
        feels = 27.5 + temp_offset
        hum = 55.0
        rain_prob = 20
        rain_mm = 0.0
        wind = 11.0
        cond = "Partly Cloudy"
        icon = "🌤"
        summary = "Favorable farming weather with moderate sunlight and balanced humidity."

    forecast_days = _generate_deterministic_forecast(
        base_temp=temp,
        base_humidity=hum,
        base_rain_prob=rain_prob,
        base_rain_mm=rain_mm,
        base_wind=wind,
        condition=cond,
        icon=icon,
    )

    return WeatherSnapshot(
        location=loc_display,
        timestamp=now_str,
        temperature=round(temp, 1),
        feels_like=round(feels, 1),
        humidity=round(hum, 1),
        precipitation_probability=rain_prob,
        precipitation_amount_mm=round(rain_mm, 1),
        wind_speed_kmh=round(wind, 1),
        wind_direction="NW",
        weather_condition=cond,
        condition_icon=icon,
        forecast_summary=summary,
        forecast_days=forecast_days,
        is_demo=True,
        source="demo_weather_simulator",
        is_available=True,
        error_message="",
    )
