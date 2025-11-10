# deliberation/multi_ai_response.py

from __future__ import annotations

from typing import Any, Dict, Optional

import streamlit as st

from deliberation.judge_ai import JudgeAI
from components.multi_ai_judge_result_view import MultiAIJudgeResultView


class MultiAIResponse:
    """
    マルチAIの応答表示 + Judge の結果表示をまとめて面倒見るクラス。

    DebugPanel からは llm_meta を丸ごと渡してもらう前提。
    """

    def __init__(self, title: str = "マルチAIレスポンス") -> None:
        self.title = title
        self.judge_ai = JudgeAI()
        self.judge_view = MultiAIJudgeResultView()

    # -- llm_meta から models を取り出すヘルパ -----------------------------

    def _extract_models(self, llm_meta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        llm_meta["models"] を優先的に見る。
        それが無い場合は、旧フォーマットを簡易的にサポート。
        """
        models = llm_meta.get("models")
        if isinstance(models, dict) and models:
            return models

        # 旧フォーマット: トップレベルに gpt4o / hermes などが直置きされているケース
        candidates: Dict[str, Any] = {}
        for key, value in llm_meta.items():
            if key in {
                "route",
                "model_main",
                "usage_main",
                "usage",
                "prompt_messages",
                "prompt_preview",
                "judge",
            }:
                continue
            if isinstance(value, dict) and ("reply" in value or "text" in value):
                candidates[key] = value

        return candidates or None

    # -- メイン描画 ---------------------------------------------------------

    def render(self, llm_meta: Optional[Dict[str, Any]]) -> None:
        st.markdown(f"#### ✏️ {self.title}")

        if not isinstance(llm_meta, dict) or not llm_meta:
            st.caption("（llm_meta が空のため、マルチAI情報は表示できません）")
            return

        # 1) モデル応答比較
        models = self._extract_models(llm_meta)
        with st.expander("🧪 モデル応答比較", expanded=True):
            if not isinstance(models, dict) or not models:
                st.caption("（models 情報がありません）")
            else:
                for key, data in models.items():
                    if not isinstance(data, dict):
                        continue

                    reply = data.get("reply") or data.get("text") or ""
                    model_name = data.get("model_name") or key
                    route = data.get("route") or llm_meta.get("route") or "unknown"

                    st.markdown(f"**{model_name}**  (_{key}_, route: `{route}`)")
                    if reply:
                        st.write(reply)
                    else:
                        st.caption("（返信テキストなし）")

                    usage = data.get("usage") or data.get("usage_main")
                    if isinstance(usage, dict):
                        pt = usage.get("prompt_tokens", "？")
                        ct = usage.get("completion_tokens", "？")
                        tt = usage.get("total_tokens", "？")
                        st.caption(
                            f"tokens: total={tt}, prompt={pt}, completion={ct}"
                        )

                    st.markdown("---")

        # 2) Judge 実行＆結果表示
        judge = llm_meta.get("judge")
        if not isinstance(judge, dict):
            # 必要であれば新たに審議を実行
            judge = self.judge_ai.run(llm_meta)

        with st.expander("⚖️ マルチAI審議結果", expanded=True):
            self.judge_view.render(judge)
