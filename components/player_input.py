# components/player_input.py

from typing import Optional
import streamlit as st


class PlayerInput:
    # テキストエリアに使うキー名
    TEXT_KEY = "player_input_text"

    def __init__(self) -> None:
        # 最初の1回だけ空文字で初期化
        if self.TEXT_KEY not in st.session_state:
            st.session_state[self.TEXT_KEY] = ""

    def render(self) -> str:
        """
        入力欄と「送信」ボタンを描画し、
        送信されたときだけそのテキストを返す。
        送信されていなければ "" を返す。
        """

        st.write("あなたの発言を入力:")

        # 🚫 value= は渡さない。key だけで状態を管理させる
        user_text: str = st.text_area(
            label="",
            key=self.TEXT_KEY,
            height=160,
        )

        send = st.button("送信", type="primary")

        if send:
            text_to_send = user_text.strip()
            if not text_to_send:
                # 空文字だけなら何もしない
                return ""

            # ✅ クリアは「送信が押された瞬間」だけ
            st.session_state[self.TEXT_KEY] = ""

            return text_to_send

        # 送信されていないとき
        return ""
