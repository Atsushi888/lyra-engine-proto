# components/player_input.py
import streamlit as st


class PlayerInput:
    """ユーザーの入力欄＋送信処理を担当"""

    def __init__(
        self,
        form_key: str = "user_input_form",
        text_key: str = "user_input_box",
    ):
        # もし変な値が渡っても絶対に空文字にならないようにする
        self.form_key = form_key or "user_input_form"
        self.text_key = text_key or "user_input_box"

    def render(self) -> str:
        """
        入力欄と「送信」ボタンを描画し、
        ボタンが押されたときにだけ確定テキストを返す。
        それ以外は空文字を返す。
        """

        # セッションにキーがなければ初期化しておく
        if self.text_key not in st.session_state:
            st.session_state[self.text_key] = ""

        # フォームにまとめると、ボタンが安定して表示される
        with st.form(key=self.form_key):
            user_input = st.text_area(
                "あなたの発言を入力:",
                key=self.text_key,
                height=160,  # 高さはお好みで
            )

            submitted = st.form_submit_button("送信")

        # ボタンが押されていて、かつ中身が空でなければ確定
        if submitted:
            text = (st.session_state.get(self.text_key, "") or "").strip()
            if text:
                # 入力欄をクリア
                st.session_state[self.text_key] = ""
                return text

        return ""
