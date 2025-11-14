# conversation_engine.py — LLM 呼び出しを統括する会話エンジン層

from typing import Any, Dict, List, Tuple

from llm_router import (
    call_with_fallback,   # GPT-4o（物語本体）
    call_hermes,          # Hermes
    call_gpt5_candidate,  # GPT-5.1（3人目候補）
)


class LLMConversation:
    """
    system プロンプト（フローリア人格など）と LLM 呼び出しをまとめた会話エンジン。

    現状：
      - メイン応答は GPT-4o（call_with_fallback）
      - 裏画面用に「gpt4o」「hermes」「gpt5」の3モデル分を llm_meta["models"] に詰める
      - MultiAIResponse / JudgeAI / ComposerAI はこの models を前提に動く
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

    # ===== LLM に渡す messages を構築 =====
    def build_messages(self, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        「system（人格＋文体指針）」＋「最新 user 発言」だけを LLM に渡す。
        """

        # 1) system（ペルソナ＋スタイルヒント）
        system_content = self.system_prompt
        effective_style_hint = self.style_hint or self.default_style_hint
        system_content += "\n\n" + effective_style_hint

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_content}
        ]

        # 2) 最新の user メッセージのみ抽出
        last_user_content: str | None = None
        for m in reversed(history):
            if m.get("role") == "user":
                last_user_content = m.get("content", "")
                break

        if last_user_content:
            messages.append({"role": "user", "content": last_user_content})
        else:
            # user が存在しない場合（初期起動時など）
            messages.append(
                {
                    "role": "user",
                    "content": (
                        "（ユーザーはまだ発言していません。"
                        "あなた＝フローリアとして、軽く自己紹介してください）"
                    ),
                }
            )

        return messages

    # ===== 実際に LLM へ投げる =====
    def generate_reply(
        self,
        history: List[Dict[str, str]],
    ) -> Tuple[str, Dict[str, Any]]:
        messages = self.build_messages(history)

        # 1) GPT-4o 本体（物語の表側）
        text_gpt, meta_gpt = call_with_fallback(
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        # 2) Hermes（OpenRouter）
        text_hermes, meta_hermes = call_hermes(
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        # 3) GPT-5.1（3人目候補フローリア）
        text_gpt5, meta_gpt5 = call_gpt5_candidate(
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        # Debug 用共通情報
        meta: Dict[str, Any] = dict(meta_gpt)
        meta["prompt_messages"] = messages
        meta["prompt_preview"] = "\n\n".join(
            f"[{m['role']}] {m['content'][:300]}"
            for m in messages
        )

        usage_gpt = meta_gpt.get("usage_main") or {}
        usage_hermes = meta_hermes.get("usage_main") or {}
        usage_gpt5 = meta_gpt5.get("usage_main") or {}

        # 裏画面用 models セクション
        meta["models"] = {
            "gpt4o": {
                "reply": text_gpt,
                "usage": usage_gpt,
                "route": meta_gpt.get("route", "gpt"),
                "model_name": meta_gpt.get("model_main", "gpt-4o"),
            },
            "hermes": {
                "reply": text_hermes,
                "usage": usage_hermes,
                "route": meta_hermes.get("route", "openrouter"),
                "model_name": meta_hermes.get("model_main", "Hermes"),
            },
            "gpt5": {
                "reply": text_gpt5,
                "usage": usage_gpt5,
                "route": meta_gpt5.get("route", "gpt5-candidate"),
                "model_name": meta_gpt5.get("model_main", "gpt-5.1"),
            },
        }

        # 表側に返すのは従来どおり GPT-4o の返答（Composer は Backstage 側で見る）
        return text_gpt, meta
