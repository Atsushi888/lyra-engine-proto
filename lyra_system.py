from auth.auth_manager import AuthManager
from auth.roles import Role
from components.mode_switcher import ModeSwitcher
import streamlit as st

class LyraSystem:
    def __init__(self) -> None:
        st.set_page_config(page_title="Lyra System", layout="wide")
        self.auth = AuthManager()
        self.switcher = ModeSwitcher(default_key="PLAY", session_key="view_mode")

    def run(self) -> None:
        if bool(st.secrets.get("auth", {}).get("bypass", False)):
            self.switcher.render(user_role=Role.ADMIN)
            return
        res = self.auth.render_login(location="main")
        if not res.status:
            st.stop()
        role = self.auth.role()
        self.switcher.render(user_role=role)

if __name__ == "__main__":
    LyraSystem().run()
