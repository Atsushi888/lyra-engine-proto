# components/chat_log.py

from typing import List, Dict
import streamlit as st
import html


class ChatLog:
    def __init__(self, partner_name: str, display_limit: int = 20000):
        self.partner_name = partner_name
        self.display_limit = display_limit

        # CSSの注入
        st.markdown(
            """
            <style>
            /* 吹き出し外枠（間隔管理） */
            .chat-bubble-container {
                margin: 10px 0;
            }
        
            /* 吹き出し本体 */
            .chat-bubble {
                border: 1px solid #ccc;
                border-radius: 8px;
                padding: 4px 10px 8px 10px; /* 上4px, 下8pxに変更 → 名前が上に詰まる */
                margin: 0;
                background-color: #f9f9f9;
                white-space: pre-wrap;
                text-align: left;
                line-height: 1.55;
            }
        
            /* 名前のスタイル */
            .chat-name {
                font-weight: bold;
                margin-bottom: 2px; /* 名前と本文の距離をわずかに空ける */
                line-height: 1.2;
            }
        
            .chat-bubble.assistant {
                background-color: #f2f2f2;
                border-color: #999;
            }
            .chat-bubble.user {
                background-color: #e8f2ff;
                border-color: #66aaff;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

    def render(self, messages: List[Dict[str, str]]) -> None:
        st.subheader("💬 会話ログ")

        if not messages:
            st.text("（まだ会話は始まっていません）")
            return

        for msg in messages[-self.display_limit:]:
            role = msg.get("role", "")
            txt = msg.get("content", "")

            if role == "assistant":
                name = self.partner_name
                role_class = "assistant"
            elif role == "user":
                name = "あなた"
                role_class = "user"
            else:
                name = role or "system"
                role_class = "assistant"

            safe_txt = html.escape(txt)

            # 吹き出しコンテナ＋本体をまとめて描画
            st.markdown(
                f"""
                <div class="chat-bubble-container">
                    <div class="chat-bubble {role_class}">
                        <div class="chat-name">{name}:</div>
                        {safe_txt}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
