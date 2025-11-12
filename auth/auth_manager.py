# auth/auth_manager.py
from __future__ import annotations
import streamlit as st
import streamlit_authenticator as stauth
from copy import deepcopy
import inspect
from .roles import Role

class AuthManager:
    def __init__(self) -> None:
        def _to_dict(sec):
            if hasattr(sec, "to_dict"):
                return sec.to_dict()
            return {k: (v.to_dict() if hasattr(v, "to_dict") else deepcopy(v))
                    for k, v in sec.items()}

        credentials = _to_dict(st.secrets["credentials"])
        cookie      = _to_dict(st.secrets.get("cookie", {}))

        self.authenticator = stauth.Authenticate(
            credentials=credentials,
            cookie_name=cookie.get("name", "lyra_auth"),
            key=cookie.get("key", "change_me"),
            cookie_expiry_days=int(cookie.get("expiry_days", 30)),
        )

    def role(self) -> Role:
        return Role.ADMIN if st.session_state.get("role") == "ADMIN" else (
               Role.USER  if st.session_state.get("authentication_status") else Role.GUEST)

    def render_login(self) -> None:
        # ---- login() のシグネチャで新旧判定して呼び分け ----
        sig = inspect.signature(self.authenticator.login)
        if "location" in sig.parameters and "form_name" not in sig.parameters:
            # 新API (>=0.4.x)
            name, auth_status, username = self.authenticator.login(
                location="main", key="auth", fields={"Form name": "Lyra System ログイン"}
            )
        else:
            # 旧API (<=0.3.x)
            name, auth_status, username = self.authenticator.login(
                "Lyra System ログイン", "main"
            )

        if auth_status:
            # 認証OK：ロール設定
            role = st.secrets["credentials"]["usernames"][username]["role"]
            st.session_state["role"] = role
            st.success(f"ログイン：{name}（{role}）")
        elif auth_status is False:
            st.error("メール / パスワードが違います。")
        else:
            st.info("メール / パスワードを入力してください。")
