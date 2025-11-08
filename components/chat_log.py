# components/chat_log.py

from typing import List, Dict
import streamlit as st

class ChatLog:
    def __init__(self, partner_name: str, display_limit: int = 20000):
        self.partner_name = partner_name
        self.display_limit = display_limit

    def render(self, messages: List[Dict[str, str]]) -> None:
        st.subheader("💬 会話ログ")

        if not messages:
            st.text("（まだ会話は始まっていません）")
            return

        # 直近 display_limit 件だけ表示
        for msg in messages[-self.display_limit:]:
            role = msg.get("role", "")
            txt  = msg.get("content", "")

            if role == "assistant":
                name = self.partner_name
            elif role == "user":
                name = "あなた"
            else:
                name = role or "system"

            # ここがポイント：プレーンテキスト＋改行
            st.text(f"{name}:\n{txt}")
