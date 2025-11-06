# components/preflight.py
from typing import Optional
import streamlit as st


class PreflightChecker:
    """APIキーの有無だけざっくり確認する軽量クラス"""

    def __init__(self, openai_key: Optional[str], openrouter_key: Optional[str]):
        self.openai_key = openai_key or ""
        self.openrouter_key = openrouter_key or ""

    def has_openai(self) -> bool:
        return bool(self.openai_key)

    def has_openrouter(self) -> bool:
        return bool(self.openrouter_key)

    def render(self) -> None:
        st.subheader("🧪 起動前診断 (Preflight)")

        if self.has_openai():
            st.success("✅ OPENAI: OpenAI API キーは有効です。")
        else:
            st.error("❌ OPENAI: OpenAI API キーが設定されていません。")

        if self.has_openrouter():
            st.success("✅ OPENROUTER: OpenRouter キー有効（Hermes 利用可）。")
        else:
            st.info("ℹ️ OPENROUTER: キー未設定のため Hermes は使用されません。")
