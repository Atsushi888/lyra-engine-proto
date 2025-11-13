# lyra_system.py — Lyra System エントリポイント

from __future__ import annotations

import streamlit as st

from auth.auth_manager import AuthManager
from auth.roles import Role
from components.mode_switcher import ModeSwitcher


class LyraSystem:
    """
    Lyra 全体を束ねるエントリポイント。

    - まず AuthManager で認証確認
    - 未ログインならログイン画面だけを表示
    - ログイン済みなら ModeSwitcher で 4 画面の切り替えを行う
    """

    def __init__(self) -> None:
        st.set_page_config(page_title="Lyra System", layout="wide")

        # 認証マネージャ
        self.auth = AuthManager()

        # 画面切り替え（PLAY / USER / BACKSTAGE / PRIVATE）
        # 実際の表示ロジックは ModeSwitcher 側に全部委譲する
        self.switcher = ModeSwitcher(
            default_key="PLAY",
            session_key="view_mode",
        )

    def _render_login_page(self) -> Role:
        """
        ログインしていない場合の画面。
        AuthManager.render_login() に UI を任せ、
        成功したら Role を返す。
        """
        st.title("🔒 Lyra System ログイン")
        st.caption("※ 現在ログインシステムは段階的に導入中です。")

        # AuthManager 側にフォーム描画＆判定を一任
        result = self.auth.render_login(location="main")

        # render_login の中で成功すると session_state が立つので、
        # role() をもう一度取り直す
        role = self.auth.role()
        return role

    def run(self) -> None:
        """
        メイン実行ループ。
        - 未ログイン: ログイン画面のみ表示して終了
        - ログイン済み: ModeSwitcher に画面切り替えを任せる
        """
        role = self.auth.role()

        # ログインしていない場合（ANON）はログイン画面へ
        if role < Role.USER:
            role = self._render_login_page()
            # まだ USER に到達していなければここで終了
            if role < Role.USER:
                return

        # ここまで来たら USER 以上が保証されているので、
        # 4 画面切り替えシステムを起動
        self.switcher.render(user_role=role)


if __name__ == "__main__":
    LyraSystem().run()
