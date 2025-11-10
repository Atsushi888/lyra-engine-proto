# components/multi_ai_response.py

from __future__ import annotations

from typing import Any, Dict, Optional
import streamlit as st

from components.multi_ai_display_config import MultiAIDisplayConfig
from components.multi_ai_model_viewer import MultiAIModelViewer
from components.multi_ai_judge_result_view import MultiAIJudgeResultView
from deliberation.judge_ai import JudgeAI  # パスはプロジェクト構成に合わせて調整してね


class MultiAIResponse:
    """
    マルチAIレスポンスシステムの中核クラス。

    ・表示対象AIの設定（MultiAIDisplayConfig）
    ・モデル応答ビュー（MultiAIModelViewer）
    ・JudgeAI による審議実行
    ・審議結果ビュー（MultiAIJudgeResultView）

    をひとまとめにした「裏画面用のマルチAI可視化モジュール」。

    DebugPanel などの上位側は、このクラスに llm_meta を渡して
    render() を呼ぶだけでよい。
    """

    def __init__(self) -> None:
        # ここで「どのAIをどう表示するか」を定義
        display_config = MultiAIDisplayConfig(
            initial={
                "gpt4o": "GPT-4o",
                "hermes": "Hermes",
                # 将来ここに "claude": "Claude 3" などを足せば拡張できる
            }
        )
        self.model_viewer = MultiAIModelViewer(display_config)
        self.judge_view = MultiAIJudgeResultView()
        self.judge_ai = JudgeAI()

    def _ensure_judge(self, llm_meta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        llm_meta の状態を見て、必要であれば JudgeAI を実行し、
        llm_meta["judge"] を埋めて返す。
        """
        if not isinstance(llm_meta, dict):
            return None

        judge = llm_meta.get("judge")
        models = llm_meta.get("models")

        if isinstance(judge, dict):
            return judge

        if not isinstance(models, dict) or len(models) < 2:
            return None

        # ここで実際に審議を実行する
        judge = self.judge_ai.run(llm_meta)
        return judge

    def render(self, llm_meta: Optional[Dict[str, Any]]) -> None:
        """
        マルチAIレスポンス全体を 1 ブロックとして描画する。

        上位からはただ llm_meta を渡して呼び出すだけでよい。
        """
        if not isinstance(llm_meta, dict) or not llm_meta:
            st.caption("（まだマルチAIレスポンスはありません）")
            return

        st.markdown("### 🧪 マルチAIレスポンス")

        # プロンプトプレビュー（任意）
        prompt_preview = llm_meta.get("prompt_preview")
        if isinstance(prompt_preview, str) and prompt_preview.strip():
            with st.expander("📝 プロンプトプレビュー", expanded=False):
                st.code(prompt_preview, language="text")

        # モデル応答比較
        models = llm_meta.get("models")
        if isinstance(models, dict) and models:
            with st.expander("🤝 モデル応答比較", expanded=True):
                self.model_viewer.render(models)
        else:
            st.caption("（models 情報がありません）")

        # JudgeAI の結果
        judge = self._ensure_judge(llm_meta)
        with st.expander("⚖️ マルチAI審議結果", expanded=True):
            self.judge_view.render(judge)
