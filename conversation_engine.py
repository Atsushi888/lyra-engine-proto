# conversation_engine.py — LLM 呼び出しを統括する会話エンジン層

from typing import Any, Dict, List, Tuple
from multi_ai.ai_response_collector import MultiAIResponseCollector
from components.multi_ai_response import PARTICIPATING_MODELS


class LLMConversation:
    """
    system プロンプト（フローリア人格など）と LLM 呼び出しをまとめた会話エンジン。
    GPT-4o と Hermes(dummy) の両方から応答を収集する。
    """

    def __init__(
        self,
        system_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 800,
        style_hint: str = "",
    ) -> None:
        self.system_prompt = system_prompt
        self.temperature = float(temperature)
        self.max_tokens = int(max_tokens)
        self.style_hint = style_hint.strip() if style_hint else ""

        # デフォルトのスタイル指針（persona に style_hint がない場合のみ使用）
        self.default_style_hint = (
            "あなたは上記の system プロンプトで定義されたキャラクターとして振る舞います。\n"
            "ユーザーは物語の本文（地の文と会話文）を日本語で入力します。\n"
            "直前のユーザーの発言や行動を読み、その続きを自然に描写してください。\n"
            "文体は自然で感情的に。見出し・記号・英語タグ（onstage:, onscreen: など）は使わず、"
            "純粋な日本語の物語文として出力してください。"
        )

        # ★ ここで「審議に参加させるAI」を定義して Collector に渡す
        self.multi_ai = MultiAIResponseCollector(
            participants=list(PARTICIPATING_MODELS.keys()),
            primary="gpt4o",
        )

    # ===== LLMに渡すmessageを構築 =====
    def build_messages(self, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        system_content = self.system_prompt
        effective_style_hint = self.style_hint or self.default_style_hint
        system_content += "\n\n" + effective_style_hint

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_content}
        ]

        last_user_content = None
        for m in reversed(history):
            if m.get("role") == "user":
                last_user_content = m.get("content", "")
                break

        if last_user_content:
            messages.append({"role": "user", "content": last_user_content})
        else:
            messages.append(
                {
                    "role": "user",
                    "content": "（ユーザーはまだ発言していません。あなた＝フローリアとして、軽く自己紹介してください）",
                }
            )
        return messages

    # ===== 実際にマルチAIへ投げる =====
    def generate_reply(
        self,
        history: List[Dict[str, str]],
    ) -> Tuple[str, Dict[str, Any]]:
        messages = self.build_messages(history)

        # Collectorにまるっとお任せ
        text, meta = self.multi_ai.collect(
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        meta = dict(meta)
        meta["prompt_messages"] = messages
        meta["prompt_preview"] = "\n\n".join(
            f"[{m['role']}] {m['content'][:300]}"
            for m in messages
        )

        return text, meta
