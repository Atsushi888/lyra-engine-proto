# components/player_input.py
from dataclasses import dataclass
import streamlit as st


@dataclass
class PlayerInput:
    TEXT_KEY: str = "player_input_text"

    def render(self) -> str:
        """プレイヤーの入力欄と送信ボタン。押された瞬間に自動クリア。"""

        # ラベル
        st.markdown("**あなたの発言を入力：**")

        # 入力欄
        user_text: str = st.text_area(
            "",
            key=self.TEXT_KEY,
            height=160,
            label_visibility="collapsed",
        )

        # 送信ボタン
        submitted = st.button("送信", type="primary")

        if submitted:
            # 送信内容を一時変数に退避
            text_to_return = user_text.strip()

            # 無条件で入力欄をクリア
            st.session_state[self.TEXT_KEY] = ""

            # 値を返す（LyraEngineが受け取って処理する）
            return text_to_return

        # 押されていなければ空文字を返す
        return ""
