# auth/auth_manager.py
from __future__ import annotations
import streamlit as st
import streamlit_authenticator as stauth
from dataclasses import dataclass
from importlib.metadata import version as pkg_version
from auth.roles import Role

@dataclass
class _AuthState:
    name: str | None = None
    username: str | None = None
    authenticated: bool | None = None

class AuthManager:
    def __init__(self) -> None:
        self._state = _AuthState()
        # st.secrets["credentials"] をそのまま渡す前提
        self.authenticator = stauth.Authenticate(
            credentials=st.secrets["credentials"],
            cookie_name=st.secrets["cookie"]["name"],
            cookie_key=st.secrets["cookie"]["key"],
            cookie_expiry_days=int(st.secrets["cookie"].get("expiry_days", 30)),
        )
        # ライブラリのバージョンで分岐準備
        try:
            self._ver = pkg_version("streamlit-authenticator")
        except Exception:
            self._ver = "0.0.0"

    def render_login(self, location: str = "main") -> None:
        allowed = {"main", "sidebar", "unrendered"}
        loc = (location or "main").strip().lower()
        if loc not in allowed:
            loc = "main"

        # v0.4.0+ は kwargs 指定、旧版は位置引数。両対応で呼ぶ。
        try:
            if self._ver >= "0.4.0":
                name, auth_status, username = self.authenticator.login(
                    location=loc,
                    key="lyra_auth_login",
                    fields={"Form name": "Lyra System ログイン"},
                )
            else:
                # 旧版は (form_name, location) の順で位置引数
                name, auth_status, username = self.authenticator.login(
                    "Lyra System ログイン",
                    loc,  # ← ここは **文字列リテラルではなく変数** を渡す
                )
        except TypeError:
            # 念のためのフォールバック（kwargs 版に倒す）
            name, auth_status, username = self.authenticator.login(
                location=loc,
                key="lyra_auth_login",
                fields={"Form name": "Lyra System ログイン"},
            )

        st.session_state["authentication_status"] = auth_status
        st.session_state["name"] = name
        st.session_state["username"] = username

        self._state.name = name
        self._state.username = username
        self._state.authenticated = auth_status

        if auth_status is True:
            st.success(f"Logged in: {name or username}")
        elif auth_status is False:
            st.error("メール / パスワードが違います。")
        else:
            st.info("メール / パスワードを入力してください。")

    def role(self) -> Role:
        # 簡易: secrets の role を参照（未設定は USER）
        if st.session_state.get("authentication_status") is True:
            uname = st.session_state.get("username")
            cred = st.secrets["credentials"]["usernames"].get(uname, {})
            role_name = str(cred.get("role", "USER")).upper()
            return Role.from_str(role_name)
        return Role.GUEST

    def logout(self) -> None:
        self.authenticator.logout("Logout", "sidebar")
