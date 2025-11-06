# components/chat_log.py
from typing import List, Dict
import html
import streamlit as st


class ChatLog:
    """会話ログの描画だけを担当"""

    def __init__(self, partner_name: str, display_limit: int = 20000):
        self.partner_name = partner_name
        self.display_limit = display_limit

    def render(self, messages: List[Dict[str, str]]) -> None:
        st.subheader("💬 会話ログ")

        dialog = [m for m in messages if m["role"] in ("user", "assistant")]

        for m in dialog:
            role = m["role"]
            raw = m["content"].strip()
            shown = (
                raw
                if len(raw) <= self.display_limit
                else (raw[: self.display_limit] + " …[truncated]")
            )
            txt = html.escape(shown)

            if role == "user":
                st.markdown(
                    f"<div class='chat-bubble user'><b>あなた：</b><br>{txt}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div class='chat-bubble assistant'><b>{self.partner_name}：</b><br>{txt}</div>",
                    unsafe_allow_html=True,
                )
