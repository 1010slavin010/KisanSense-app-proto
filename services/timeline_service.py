"""Lightweight Farm Activity and Advisory Timeline Service for KisanSense.

Tracks key farm events, sensor state changes, irrigation triggers, and plant screening history.
Operates with in-memory session persistence, ready for future database storage.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
import streamlit as st


@dataclass
class TimelineEvent:
    """Represents a discrete agricultural activity or system advisory milestone."""

    id: str
    event_type: str  # "sensor_offline", "sensor_online", "irrigation", "soil", "vision", "weather", "profile"
    title: str
    description: str
    timestamp: str
    icon: str
    severity: str = "info"  # "good" | "warning" | "alert" | "info"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "title": self.title,
            "description": self.description,
            "timestamp": self.timestamp,
            "icon": self.icon,
            "severity": self.severity,
        }


def init_timeline() -> None:
    """Initialize timeline history in session state if not present."""
    if "farm_timeline" not in st.session_state:
        st.session_state.farm_timeline = []
        seed_default_timeline()


def seed_default_timeline() -> None:
    """Seed a realistic timeline based on recent activities."""
    now = datetime.now()
    events = [
        TimelineEvent(
            id="evt_init_1",
            event_type="profile",
            title="Farm Profile Initialized",
            description="Active field profile and agronomic parameters synchronized.",
            timestamp=(now - timedelta(hours=3)).strftime("%I:%M %p"),
            icon="🌾",
            severity="good",
        ),
        TimelineEvent(
            id="evt_init_2",
            event_type="sensor_online",
            title="ESP32 Telemetry Linked",
            description="Soil moisture and climate sensor probe synchronized.",
            timestamp=(now - timedelta(hours=2, minutes=15)).strftime("%I:%M %p"),
            icon="📶",
            severity="good",
        ),
        TimelineEvent(
            id="evt_init_3",
            event_type="weather",
            title="Weather Advisory Generated",
            description="3-day agricultural microclimate forecast evaluated.",
            timestamp=(now - timedelta(hours=1)).strftime("%I:%M %p"),
            icon="🌤",
            severity="info",
        ),
    ]
    st.session_state.farm_timeline = events


def record_timeline_event(
    event_type: str,
    title: str,
    description: str,
    icon: str | None = None,
    severity: str = "info",
) -> None:
    """Append a new event to the farm timeline, maintaining maximum 30 events."""
    now_str = datetime.now().strftime("%I:%M %p")
    default_icons = {
        "sensor_offline": "⚠️",
        "sensor_online": "📶",
        "irrigation": "💧",
        "soil": "🌱",
        "vision": "📷",
        "weather": "🌤",
        "heat": "🌡️",
        "profile": "🌾",
    }
    use_icon = icon or default_icons.get(event_type, "📌")
    evt_id = f"evt_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"

    new_event = TimelineEvent(
        id=evt_id,
        event_type=event_type,
        title=title,
        description=description,
        timestamp=now_str,
        icon=use_icon,
        severity=severity,
    )

    if "farm_timeline" not in st.session_state:
        st.session_state.farm_timeline = []

    # Prevent duplicate identical consecutive events
    if st.session_state.farm_timeline:
        last = st.session_state.farm_timeline[0]
        if last.event_type == event_type and last.title == title:
            return

    st.session_state.farm_timeline.insert(0, new_event)
    # Trim to 30 events
    st.session_state.farm_timeline = st.session_state.farm_timeline[:30]


def get_timeline_events(limit: int = 10) -> list[TimelineEvent]:
    """Retrieve recent farm timeline events sorted most recent first."""
    if "farm_timeline" not in st.session_state or not st.session_state.farm_timeline:
        init_timeline()
    return list(st.session_state.farm_timeline)[:limit]
