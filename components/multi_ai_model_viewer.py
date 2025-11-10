from __future__ import annotations
from typing import Any, Dict
import streamlit as st

from components.multi_ai_display_config import MultiAIDisplayConfig


class MultiAIModelViewer:
    """
    MultiAIDisplayConfig の指示に従って llm_meta['models'] を描画するビュー。
    表示ロジックのみ。models の構造には優しく。
    """

    def __init__(self, config: MultiAIDisplayConfig) -> None:
        self.config = config

    def render(self, models: Dict[str, Any]) -> None:
        st.markdown("#### 🤖 モデル応答比較")

        if not isinstance(models, dict) or not models:
            st.caption("（表示可能なモデルがありません）")
            return

        # 新しいモデルを設定に取り込んでおく（未登録モデル対策）
        self.config.ensure_from_models(models)

        visible = self.config.get_visible_models(models)
        if not visible:
            st.caption("（表示可能なモデルがありません）")
            return

        for key, label in visible:
            info = models.get(key)
            if not isinstance(info, dict):
                st.markdown(f"**{label}** (`{key}`)")
                st.caption("（情報が不正）")
                st.markdown("---")
                continue

            reply = info.get("reply") or info.get("text") or "（返信なし）"
            st.markdown(f"**{label}**  (`{key}`)")
            st.write(reply)

            usage = info.get("usage") or info.get("usage_main")
            if isinstance(usage, dict) and usage:
                pt = usage.get("prompt_tokens", "？")
                ct = usage.get("completion_tokens", "？")
                tt = usage.get("total_tokens", "？")
                st.caption(f"tokens: total={tt}, prompt={pt}, completion={ct}")

            st.markdown("---")
