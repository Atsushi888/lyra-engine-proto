from __future__ import annotations
from typing import Any, Dict, Optional
import streamlit as st


class MultiAIJudgeResultView:
    """
    判定結果を「受け取って表示するだけ」のビュー。
    judge dict は judge_ai.py が作る想定。
    """

    def __init__(self, title: str = "Multi AI Judge") -> None:
        self.title = title

    def render(self, judge: Optional[Dict[str, Any]]) -> None:
        st.markdown(f"#### ⚖️ {self.title}")

        if not isinstance(judge, dict):
            st.caption("（審議結果はまだありません）")
            return

        winner = judge.get("winner", "？")
        score = judge.get("score_diff", 0.0)
        comment = judge.get("comment", "")

        cols = st.columns(2)
        cols[0].metric("勝者", winner)
        cols[1].metric(
            "スコア差",
            f"{score:.2f}" if isinstance(score, (int, float)) else score,
        )

        if comment:
            st.markdown("**理由:**")
            st.write(comment)

        with st.expander("🪶 JudgeAI raw", expanded=False):
            raw = judge.get("raw")
            if raw:
                st.code(str(raw), language="text")
            pair = judge.get("pair")
            if pair:
                st.caption(f"比較ペア: {pair}")
