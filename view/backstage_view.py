# views/backstage_view.py
from __future__ import annotations
import streamlit as st
from components.debug_panel import DebugPanel

class BackstageView:
    def render(self) -> None:
        llm_meta = st.session_state.get("llm_meta")
        DebugPanel(title="Lyra Backstage – Multi AI Debug View").render(llm_meta)
