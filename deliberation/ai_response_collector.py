# deliberation/ai_response_collector.py

from __future__ import annotations

from typing import Any, Dict, List, Tuple


from deliberation.multi_ai_response import PARTICIPATING_MODELS
from llm_router import call_with_fallback  # GPT-4o 用（既存）
# 将来、本物 Hermes を呼ぶときは:
# from llm_router import call_hermes


class MultiAIResponseCollector:
    """
    複数AIからの応答をまとめて収集する専用クラス。

    ・participants で「どのAIを呼ぶか」を指定
    ・collect() に messages / temperature / max_tokens を渡すと、
      メインのテキストと llm_meta を返す
    ・llm_meta["models"] に各AIの応答を詰める
    """

    def __init__(
        self,
        participants: List[str],
        primary: str = "gpt4o",
    ) -> None:
        """
        participants: ["gpt4o", "hermes", ...] のようなキー一覧
        primary: 表側に出すメインAIのキー（通常 gpt4o）
        """
        self.participants = list( PARTICIPATING_MODELS.keys() )
        self.primary = primary

    def collect(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        max_tokens: int,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        各参加AIからの応答を収集し、(primary_text, llm_meta) を返す。
        """
        models: Dict[str, Any] = {}
        meta_all: Dict[str, Any] = {}

        # 1) GPT-4o（既存の call_with_fallback を利用）
        if "gpt4o" in self.participants:
            text_gpt, meta_gpt = call_with_fallback(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            usage_gpt = meta_gpt.get("usage_main") or meta_gpt.get("usage") or {}

            models["gpt4o"] = {
                "reply": text_gpt,
                "usage": usage_gpt,
                "route": meta_gpt.get("route", "gpt"),
                "model_name": meta_gpt.get("model_main", "gpt-4o"),
            }

            # 全体メタのベースは GPT 側を使う
            meta_all.update(meta_gpt)

        # 2) Hermes（いまはダミー：GPT-4o と同じ内容を別モデル扱い）
        if "hermes" in self.participants:
            if "gpt4o" in models:
                text_hermes = models["gpt4o"]["reply"]
                usage_hermes = models["gpt4o"]["usage"]
            else:
                # 将来、本物 Hermes だけ呼ぶパスを作りたければここに入れる
                text_hermes = ""
                usage_hermes = {}

            models["hermes"] = {
                "reply": text_hermes,
                "usage": usage_hermes,
                "route": "dummy-hermes",
                "model_name": "Hermes (dummy)",
            }

        # primary のテキストを決める（デフォルトは gpt4o）
        primary_text = ""
        if self.primary in models:
            primary_text = models[self.primary]["reply"]
        elif models:
            # 予備：何か一つでもあれば先頭を返す
            first_key = next(iter(models.keys()))
            primary_text = models[first_key]["reply"]

        # llm_meta に models を載せて返す
        meta_all["models"] = models
        meta_all["multi_ai_participants"] = list(models.keys())

        return primary_text, meta_all
