# components/debug_panel.py
from typing import Any, Dict, Optional
import streamlit as st


class DebugPanel:
    """LLM 呼び出しメタ情報を出すだけの簡易デバッグパネル"""

    def __init__(self, checkbox_label: str = "🧠 デバッグを表示"):
        self.checkbox_label = checkbox_label
        self._meta: Optional[Dict[str, Any]] = None

    def update(self, meta: Optional[Dict[str, Any]]) -> None:
        """外側から meta だけ更新したいとき用（オプション）"""
        self._meta = meta

    def render(self, meta: Optional[Dict[str, Any]] = None) -> None:
        """
        デバッグパネル描画。
        - meta が渡されればそれを内部に保存
        - 渡されなければ最後に保存したもの（_meta）を使う
        """
        if meta is not None:
            self._meta = meta

        show = st.checkbox(self.checkbox_label, False, key="debug_panel_show")
        if not show:
            return

        st.markdown("###### 最後の LLM 呼び出し情報")
        if self._meta:
            st.json(self._meta)
        else:
            st.info("まだ LLM 呼び出し情報はありません。")
