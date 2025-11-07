# conversation_engine.py — LLM 呼び出しを統括する会話エンジン層
import os
from typing import Any, Dict, List, Tuple

from llm_router import call_with_fallback


class LLMConversation:
    """
    system プロンプトと LLM 呼び出しをまとめた会話エンジン層。
    将来的にキャラAI制御、感情状態、モード切替などの拡張もここに統合。
    """

    def __init__(
        self,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 800,
    ) -> None:
        self.system_prompt = system_prompt
        self.temperature = float(temperature)
        self.max_tokens = int(max_tokens)

    # ===== メッセージ構築 =====
    def build_messages(self, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        system プロンプト + 会話履歴を LLM API 向けに整形。
        """
        llm_messages: List[Dict[str, str]] = [
            {"role": "system", "content": self.system_prompt}
        ]
        llm_messages.extend(history)
        return llm_messages

    # ===== 応答生成 =====
    def generate_reply(
        self,
        history: List[Dict[str, str]],
    ) -> Tuple[str, Dict[str, Any]]:
        """
        llm_router.call_with_fallback() を呼び出し、
        LLM 応答とメタ情報を返す。
        """
        messages = self.build_messages(history)
        text, meta = call_with_fallback(
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        return text, meta
