# views/private_view.py
from __future__ import annotations
import streamlit as st
from components.user_window import UserWindowPanel

class PrivateView:
    def render(self) -> None:
        st.info("※ 公開版では表示されません。開発者専用。")
        UserWindowPanel().render()
