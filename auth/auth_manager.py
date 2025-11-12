from __future__ import annotations
from typing import Optional, Tuple

import streamlit as st
import streamlit_authenticator as stauth

from .roles import Role


class AuthManager:
    """
    streamlit-authenticator を薄くラップする認証管理。
    - 画面：login / logout ボタンはこの中で描画
    - 状態：現在ロールは self._role に保持（LyraSystemからは role() だけ使う）
    - 既存の LyraSystem 側 API（role()/render_login()）は不変
    """

    def __init__(self) -> None:
        self._role: Role = Role.GUEST
        self._auth: Optional[stauth.Authenticate] = None
        self._username: Optional[str] = None
        self._name: Optional[str] = None
        self._auth_status: Optional[bool] = None

        # secrets.toml の存在チェック（なければソフトに案内）
        if "credentials" not in st.secrets:
            st.warning(
                "⚠️ `st.secrets` に `credentials` がありません。"
                " secrets.toml を設定してください。"
            )

        self._init_authenticator()

    # --------- 公開API ----------
    def role(self) -> Role:
        return self._role

    def render_login(self) -> None:
        """
        ログインUIを表示。成功時は sidebar にログアウトボタンも表示。
        認証OKなら self._role を更新する。
        """
        name, auth_status, username = self._login_box()
        self._auth_status = auth_status
        self._name = name if auth_status else None
        self._username = username if auth_status else None

        if auth_status:
            # ロールを secrets から取得（なければ USER）
            self._role = self._resolve_role_from_username(username)
            st.sidebar.write(f"👤 {name} ({self._role.name})")
            if self._auth:
                self._auth.logout("ログアウト", "sidebar")
        elif auth_status is False:
            st.error("認証に失敗しました。")
        else:
            st.info("メール / パスワードを入力してください。")

    # --------- 内部 ----------
    def _init_authenticator(self) -> None:
        creds = st.secrets.get("credentials", {})
        cookie = st.secrets.get("cookie", {})
        try:
            self._auth = stauth.Authenticate(
                credentials=creds,
                cookie_name=cookie.get("name", "lyra_auth"),
                key=cookie.get("key", "lyra_secret"),
                cookie_expiry_days=cookie.get("expiry_days", 7),
            )
        except Exception as e:
            self._auth = None
            st.error(f"Authenticator 初期化に失敗: {e}")

    def _login_box(self) -> Tuple[Optional[str], Optional[bool], Optional[str]]:
        """
        streamlit-authenticator の login を呼び出す。
        returns: (name, auth_status, username)
        """
        if not self._auth:
            # フォールバックUI（secrets未設定時など）
            st.text_input("ユーザー (表示のみ)", key="fallback_user")
            st.text_input("パスワード (表示のみ)", type="password", key="fallback_pass")
            st.button("ログイン（無効）")
            return None, None, None

        return self._auth.login("ログイン", "main")

    def _resolve_role_from_username(self, username: Optional[str]) -> Role:
        """
        secrets.toml の credentials.usernames.<username>.role を Role にマップ
        """
        try:
            if not username:
                return Role.USER
            role_str = (
                st.secrets["credentials"]["usernames"][username]
                .get("role", "USER")
                .upper()
            )
            return Role[role_str] if role_str in Role.__members__ else Role.USER
        except Exception:
            return Role.USER
