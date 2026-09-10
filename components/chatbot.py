"""Reusable "Ask KisanSense" chatbot component, shown on the Home and Assistant pages.

Conversation history lives in st.session_state (initialized in
app.py) so it persists for the browser session. Responses come from
services/ai_service.py with active farm context and live sensor telemetry
injected into context.
"""

from __future__ import annotations

from typing import Any
import streamlit as st

from services.ai_service import get_ai_response
from services.farm_service import get_farm_context
from utils.translations import t


def render_chatbot(
    reading: Any | None = None,
    farm_context: dict[str, Any] | None = None,
) -> None:
    st.markdown(
        f'<div style="margin-top: 0.5rem; margin-bottom: 0.75rem;">'
        f'<div class="assistant-title">🤖 {t("assistant_title")}</div>'
        f'<p class="assistant-subtitle">{t("assistant_subtitle")}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.chat_messages:
        with st.chat_message("assistant", avatar="🌾"):
            st.write(t("assistant_welcome"))

    for message in st.session_state.chat_messages:
        avatar = "🌾" if message["role"] == "assistant" else None
        with st.chat_message(message["role"], avatar=avatar):
            st.write(message["content"])

    preset_prompt = st.session_state.pop("preset_assistant_prompt", None)
    prompt = preset_prompt or st.chat_input(t("assistant_placeholder"))
    if prompt:
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        farm_ctx = farm_context if farm_context is not None else get_farm_context()
        context: dict[str, Any] = {"page": st.session_state.get("page", "home"), **farm_ctx}

        active_reading = reading
        if active_reading is None:
            active_reading = st.session_state.get("sensor_reading")
        if active_reading is None:
            try:
                from services.sensor_service import get_current_sensor_data
                active_reading = get_current_sensor_data(farm_context=farm_ctx)
                st.session_state.sensor_reading = active_reading
            except Exception:
                active_reading = None

        if "latest_vision_result" in st.session_state and st.session_state.latest_vision_result is not None:
            context["vision_result"] = st.session_state.latest_vision_result

        if active_reading is not None:
            context["reading"] = active_reading
            context["soil_moisture"] = getattr(active_reading, "soil_moisture", None)
            context["temperature"] = getattr(active_reading, "temperature", None)
            context["humidity"] = getattr(active_reading, "humidity", None)
            context["sensor_online"] = getattr(active_reading, "is_online", True)
            context["last_updated"] = getattr(active_reading, "last_updated", "")
            context["sensor_condition"] = getattr(active_reading, "condition", "NORMAL")
            context["raw_status"] = getattr(active_reading, "raw_status", "ok")

            try:
                from services.farm_intelligence import evaluate_farm_intelligence
                context["intelligence"] = evaluate_farm_intelligence(
                    active_reading,
                    farm_context=farm_ctx,
                    vision_result=context.get("vision_result"),
                )
            except Exception:
                pass

        weather_snap = st.session_state.get("latest_weather_snapshot")
        if weather_snap is None:
            try:
                from services.weather_service import get_weather_snapshot
                loc = farm_ctx.get("location", "Mandya, Karnataka")
                weather_snap = get_weather_snapshot(location=loc, condition_hint=st.session_state.get("sim_condition", "NORMAL"))
                st.session_state.latest_weather_snapshot = weather_snap
            except Exception:
                weather_snap = None

        if weather_snap is not None:
            context["weather"] = weather_snap
            try:
                from services.weather_intelligence import evaluate_weather_intelligence
                context["weather_insight"] = evaluate_weather_intelligence(
                    weather_snap,
                    active_reading,
                    farm_ctx,
                    context.get("intelligence"),
                    context.get("vision_result"),
                )
            except Exception:
                pass

        response = get_ai_response(prompt, context=context)

        st.session_state.chat_messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant", avatar="🌾"):
            st.write(response)
