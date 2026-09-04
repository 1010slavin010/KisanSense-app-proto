"""Reusable "Ask KisanSense" chatbot component, shown on the Home page.

Conversation history lives in st.session_state (initialized in
app.py) so it persists for the browser session. Responses come from
services/ai_service.py, a mock implementation in Phase 1 and the
intended integration point for a real LLM later.
"""

import streamlit as st

from services.ai_service import get_ai_response
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
        response = get_ai_response(prompt, context={"page": "home"})
        st.session_state.chat_messages.append({"role": "assistant", "content": response})
        st.rerun()
