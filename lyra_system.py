from __future__ import annotations
import streamlit as st
from auth.auth_manager import AuthManager
from auth.roles import Role
from components.mode_switcher import ModeSwitcher

class LyraSystem:
    def __init__(self) -> None:
        st.set_page_config(page_title="Lyra System", layout="wide")
        self.auth = AuthManager()
        self.switcher = ModeSwitcher(default_key="PLAY", session_key="view_mode")

    def run(self) -> None:
        role = self.auth.role()
        if role < Role.USER:
            self.auth.render_login()
            st.stop()
        self.switcher.render(user_role=role)

if __name__ == "__main__":
    LyraSystem().run()
