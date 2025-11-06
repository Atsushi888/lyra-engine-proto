# components/debug_panel.py
from typing import Any, Dict, Optional
import streamlit as st


class DebugPanel:
    """LLM 呼び出しメタ情報を出すだけの簡易デバッグパネル"""

    def __init__(self, checkbox_label: str = "🧠 デバッグを表示"):
        self.checkbox_label = checkbox_label

    def render(self, meta: Optional[Dict[str, Any]]) -> None:
        show = st.checkbox(self.checkbox_label, False)
        if not show:
            return

        st.markdown("###### 最後の LLM 呼び出し情報")
        if meta:
            st.json(meta)
        else:
            st.info("まだ LLM 呼び出し情報はありません。")
