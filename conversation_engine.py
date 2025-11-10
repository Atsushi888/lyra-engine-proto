# conversation_engine.py — LLM 呼び出しを統括する会話エンジン層

from typing import Any, Dict, List, Tuple

from llm_router import call_with_fallback


class LLMConversation:
    """
    system プロンプト（フローリア人格など）と LLM 呼び出しをまとめた会話エンジン。
    GPT-4o に対して、
    「system_prompt + （style_hint） + 直近の user メッセージ」
    を渡し、応答を生成する。
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

    # ===== LLMに渡すmessageを構築 =====
    def build_messages(self, history: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        「system（人格＋文体指針）」＋「最新user発言」だけをLLMに渡す。
        """

        # 1) system（ペルソナ＋スタイルヒント）
        system_content = self.system_prompt
        effective_style_hint = self.style_hint or self.default_style_hint
        system_content += "\n\n" + effective_style_hint

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_content}
        ]

        # 2) 最新の user メッセージのみ抽出
        last_user_content = None
        for m in reversed(history):
            if m.get("role") == "user":
                last_user_content = m.get("content", "")
                break

        if last_user_content:
            messages.append({"role": "user", "content": last_user_content})
        else:
            # userが存在しない場合（初期起動時など）
            messages.append(
                {
                    "role": "user",
                    "content": "（ユーザーはまだ発言していません。"
                               "あなた＝フローリアとして、軽く自己紹介してください）",
                }
            )

        return messages

    # ===== 実際に GPT-4o に投げる =====
    def generate_reply(
        self,
        history: List[Dict[str, str]],
    ) -> Tuple[str, Dict[str, Any]]:
        """
        会話履歴を受け取り、LLM応答テキストとメタ情報を返す。
        MultiAIResponse 用に llm_meta['models'] を構築して返す。
        """
        messages = self.build_messages(history)

        # ==== メイン応答 (GPT-4o) ====
        text, meta = call_with_fallback(
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

        meta = dict(meta)  # 安全に編集できるようにコピー

        # ===== DebugPanel / MultiAIResponse 用情報 =====
        meta["prompt_messages"] = messages
        meta["prompt_preview"] = "\n\n".join(
            f"[{m['role']}] {m['content'][:300]}"
            for m in messages
        )

        # ==== ★ ここが重要：MultiAIResponseへのデータ供給 ====
        # 将来的に Hermes や Claude を追加しやすいように dict 形式で構築
        usage_main = meta.get("usage_main") or meta.get("usage") or {}

        meta["models"] = {
            "gpt4o": {
                "reply": text,
                "usage": usage_main,
                "route": meta.get("route", "gpt"),
                "model_name": meta.get("model_main", "gpt-4o"),
            }
        }

        # Hermesなど別AIを追加する場合は、ここに追記すればOK。
        # meta["models"]["hermes"] = {
        #     "reply": hermes_text,
        #     "usage": hermes_usage,
        #     "route": "hermes",
        #     "model_name": "Mistral-Hermes-3",
        # }

        return text, meta
