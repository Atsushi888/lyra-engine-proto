# deliberation/participating_models.py
# マルチAI審議に参加するモデル一覧を一元管理するモジュール

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class ModelInfo:
    key: str          # 内部キー（models dict のキー）
    label: str        # 画面表示名
    description: str  # 説明（デバッグ用）


PARTICIPATING_MODELS: Dict[str, ModelInfo] = {
    # メインの物語生成モデル
    "gpt4o": ModelInfo(
        key="gpt4o",
        label="GPT-4o",
        description="OpenAI メインモデル（物語本文担当）。",
    ),
    # OpenRouter 経由 Hermes
    "hermes": ModelInfo(
        key="hermes",
        label="Hermes",
        description="OpenRouter / Hermes モデル。",
    ),
    # Judge 兼 第3の候補モデル（実体は OPENAI_JUDGE_MODEL）
    "judge": ModelInfo(
        key="judge",
        label="Judge (GPT-5.1)",
        description="審判用モデル（環境変数 OPENAI_JUDGE_MODEL で指定）。",
    ),
}

__all__ = ["ModelInfo", "PARTICIPATING_MODELS"]
