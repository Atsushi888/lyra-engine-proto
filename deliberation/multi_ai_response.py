# deliberation/multi_ai_response.py
# マルチAIの応答表示 ＋ Judge 結果表示の中核クラス

from __future__ import annotations

from typing import Any, Dict, Optional

import streamlit as st

from components.multi_ai_display_config import MultiAIDisplayConfig
from components.multi_ai_model_viewer import MultiAIModelViewer
from components.multi_ai_judge_result_view import MultiAIJudgeResultView
from judge_ai import JudgeAI


# このセッションで「審議に参加させるAI」の一覧
PARTICIPATING_MODELS: Dict[str, str] = {
    "gpt4o": "GPT-4o",
    "hermes": "Hermes",
}


class MultiAIResponse:
    """
    マルチAIレスポンスシステムの中核。

    ・モデル応答比較（MultiAIModelViewer）
    ・JudgeAI による審議実行
    ・審議結果表示（MultiAIJudgeResultView）

    DebugPanel 側は、llm_meta を渡して render() を呼ぶだけでよい。
    """

    def __init__(self, title: str = "マルチAIレスポンス") -> None:
        self.title = title

        # 表示対象AIの設定
        display_config = MultiAIDisplayConfig(initial=PARTICIPATING_MODELS)

        # ビュー／Judge の初期化
        self.model_viewer = MultiAIModelViewer(display_config)
        self.judge_view = MultiAIJudgeResultView()
        self.judge_ai = JudgeAI()

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------
    def _empty_judge(self, reason: str = "") -> Dict[str, Any]:
        """
        エラー時や未判定時に使う judge のガワ（ひな型）。
        """
        return {
            "winner": None,
            "score_diff": 0.0,
            "comment": reason,
            "raw": None,
            "pair": None,
        }

    def _ensure_models(self, llm_meta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        llm_meta["models"] を取り出す。
        形式が不正 or 空なら None を返す。
        """
        models = llm_meta.get("models")
        if isinstance(models, dict) and models:
            return models
        return None

    def _ensure_judge(self, llm_meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        llm_meta の状態を見て、必要であれば JudgeAI を実行し、
        必ず dict 形式の judge を返す（None は返さない）。
        """
        if not isinstance(llm_meta, dict):
            return self._empty_judge("llm_meta が存在しません。")

        # すでに judge が dict として保存されていればそれを使う
        judge = llm_meta.get("judge")
        if isinstance(judge, dict):
            return judge

        # models が 2 つ未満ならそもそも審議不能
        models = self._ensure_models(llm_meta)
        if not isinstance(models, dict) or len(models) < 2:
            return self._empty_judge("有効なモデル数が 2 未満のため、審議できません。")

        # ここで JudgeAI を実行
        try:
            judge = self.judge_ai.run(llm_meta)
        except Exception as e:
            return self._empty_judge(f"JudgeAI 実行中にエラー: {e}")

        if isinstance(judge, dict):
            # 後続の再表示のために llm_meta にも保存しておく
            llm_meta["judge"] = judge
            return judge

        return self._empty_judge("JudgeAI が不正な形式の結果を返しました。")

    # ------------------------------------------------------------------
    # public
    # ------------------------------------------------------------------
    def render(self, llm_meta: Optional[Dict[str, Any]]) -> None:
        """
        マルチAIレスポンス全体（モデル比較＋審議結果）を描画する。
        DebugPanel などの上位からは llm_meta を渡して呼ぶだけでよい。
        """
        st.markdown(f"### ✒️ {self.title}")

        if not isinstance(llm_meta, dict) or not llm_meta:
            st.caption("（まだマルチAIレスポンスはありません）")
            return

        # ---- プロンプトプレビュー ----
        prompt_preview = llm_meta.get("prompt_preview")
        if isinstance(prompt_preview, str) and prompt_preview.strip():
            with st.expander("📝 プロンプトプレビュー", expanded=False):
                st.code(prompt_preview, language="text")

        # ---- モデル応答比較 ----
        models = self._ensure_models(llm_meta)
        if models:
            with st.expander("🤝 モデル応答比較", expanded=True):
                self.model_viewer.render(models)
        else:
            st.caption("（models 情報がありません）")

        # ---- Judge 結果 ----
        judge = self._ensure_judge(llm_meta)
        with st.expander("⚖️ マルチAI審議結果", expanded=True):
            self.judge_view.render(judge)
