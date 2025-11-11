from __future__ import annotations

from typing import Any, Dict


from deliberation.multi_ai_response import PARTICIPATING_MODELS


class AIResponseCollector:
    """
    将来的に「複数AIから一括でレスポンスを集める」係。
    今は最低限、llm_meta["models"] を組み立てるダミー実装。
    """

    def __init__(self) -> None:
        self.participating_models = PARTICIPATING_MODELS

    def attach_models(
        self,
        llm_meta: Dict[str, Any],
        base_reply_text: str,
        base_usage: Dict[str, Any] | None,
    ) -> None:
        """
        llm_meta に models セクションを保証する。
        とりあえず GPT-4o と Hermes を同じ内容で入れるダミー。
        """

        if base_usage is None:
            base_usage = {}

        models: Dict[str, Any] = {}

        models["gpt4o"] = {
            "reply": base_reply_text,
            "usage": base_usage,
            "route": llm_meta.get("route", "gpt"),
            "model_name": llm_meta.get("model_main", "gpt-4o"),
        }

        models["hermes"] = {
            "reply": base_reply_text,  # ★実際には Hermes の返答を入れる予定
            "usage": base_usage,
            "route": "openrouter",
            "model_name": "nousresearch/hermes-4-70b",
        }

        llm_meta["models"] = models
