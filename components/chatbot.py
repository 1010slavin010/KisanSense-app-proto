"""Reusable "Ask KisanSense" chatbot component, shown on the Home page.

Conversation history lives in st.session_state (initialized in
app.py) so it persists for the browser session. Responses come from
services/ai_service.py with active farm context and live sensor telemetry
injected into context.
"""

from __future__ import annotations

import streamlit as st

from services.ai_service import get_ai_response
from services.farm_service import get_farm_context
from utils.translations import t


def render_chatbot() -> None:
    st.markdown(f'<div class="assistant-title">{t("assistant_title")}</div>', unsafe_allow_html=True)
    st.markdown(f'<p class="assistant-subtitle">{t("assistant_subtitle")}</p>', unsafe_allow_html=True)

    if not st.session_state.chat_messages:
        with st.chat_message("assistant", avatar="🌾"):
            st.write(t("assistant_welcome"))

    for message in st.session_state.chat_messages:
        avatar = "🌾" if message["role"] == "assistant" else None
        with st.chat_message(message["role"], avatar=avatar):
            st.write(message["content"])

    prompt = st.chat_input(t("assistant_placeholder"))
    if prompt:
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)

        farm_ctx = get_farm_context()
        context = {"page": "home", **farm_ctx}

        if "sensor_reading" in st.session_state:
            reading = st.session_state.sensor_reading
            context["soil_moisture"] = getattr(reading, "soil_moisture", None)
            context["temperature"] = getattr(reading, "temperature", None)
            context["humidity"] = getattr(reading, "humidity", None)
            context["sensor_online"] = getattr(reading, "is_online", True)
            context["last_updated"] = getattr(reading, "last_updated", "")
            context["sensor_condition"] = getattr(reading, "condition", "NORMAL")
            context["raw_status"] = getattr(reading, "raw_status", "ok")

            try:
                from services.farm_intelligence import evaluate_farm_intelligence
                context["intelligence"] = evaluate_farm_intelligence(reading, farm_context=farm_ctx)
            except Exception:
                pass

        response = get_ai_response(prompt, context=context)

        st.session_state.chat_messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant", avatar="🌾"):
            st.write(response)
