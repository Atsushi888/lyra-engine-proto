# components/multi_ai_judge_result_view.py

from __future__ import annotations
from typing import Any, Dict, Optional
import streamlit as st


class MultiAIJudgeResultView:
    """
    判定結果を「受け取って表示するだけ」のビュー。
    judge は必ず dict を想定（fallback側で空dictを作る）。
    """

    def __init__(self, title: str = "Multi AI Judge") -> None:
        self.title = title

    def render(self, judge: Dict[str, Any] | None) -> None:
        if not isinstance(judge, dict):
            st.caption("（審議結果はまだありません）")
            return

        winner = judge.get("winner") or "―"
        score_diff = judge.get("score_diff", 0.0)
        comment = judge.get("comment") or ""

        st.subheader("⚖️ Multi AI Judge")
        cols = st.columns(2)
        cols[0].markdown(f"**勝者**\n\n{winner}")
        cols[1].markdown(f"**スコア差**\n\n{score_diff:.2f}")

        st.markdown("**理由:**")
        st.write(comment if comment else "（理由テキストなし）")

        raw_json = judge.get("raw_json")
        raw_text = judge.get("raw_text")

        with st.expander("🪵 JudgeAI raw"):
            if isinstance(raw_json, dict):
                st.caption("parsed JSON")
                st.json(raw_json)
            if isinstance(raw_text, str):
                st.caption("original text")
                st.code(raw_text, language="json")

            pair = judge.get("pair")
            if isinstance(pair, dict):
                st.caption("比較ペア")
                st.write(pair)                st.caption(f"比較ペア: {pair}")
