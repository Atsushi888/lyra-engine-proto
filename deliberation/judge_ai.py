# deliberation/judge_ai.py
# マルチAIの応答を「どれが良いか」判断する審判AI

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Tuple

from openai import OpenAI, BadRequestError

from deliberation.participating_models import PARTICIPATING_MODELS


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
# 審判用モデル名（デフォルトは MAIN_MODEL と同じ）
OPENAI_MAIN_MODEL = os.getenv("OPENAI_MAIN_MODEL", "gpt-4o")
OPENAI_JUDGE_MODEL = os.getenv("OPENAI_JUDGE_MODEL", OPENAI_MAIN_MODEL)


class JudgeAI:
    """
    複数モデルの応答から「どれが良いか」を JSON で判定してくれる審判。

    - 入力: llm_meta（llm_router / conversation_engine が組んだもの）
    - 参照: llm_meta["models"] = { model_key: {"reply": "..."} }
    - 出力: dict
        {
          "winner": "gpt4o" | "hermes" | "judge" | "tie",
          "score_diff": 0.8,
          "comment": "～～～"
        }
    """

    def __init__(self) -> None:
        if not OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY が設定されていないため JudgeAI を初期化できません。")
        self.client = OpenAI(api_key=OPENAI_API_KEY)

    # ===== 外向け API =====
    def run(self, llm_meta: Dict[str, Any]) -> Dict[str, Any]:
        models: Dict[str, Any] = llm_meta.get("models", {})
        if not isinstance(models, dict) or len(models) < 2:
            return {
                "winner": "none",
                "score_diff": 0.0,
                "comment": "比較対象モデルが 2 つ未満のため、審判を実行しませんでした。",
                "raw_text": "",
                "parsed": None,
            }

        messages = self._build_messages(models)
        raw_text, ok, parsed = self._call_judge(messages)

        if not ok or not isinstance(parsed, dict):
            # 失敗時は簡単な fallback
            return {
                "winner": "none",
                "score_diff": 0.0,
                "comment": "Judge モデルから有効な JSON を得られませんでした。",
                "raw_text": raw_text,
                "parsed": parsed,
            }

        # parsed に winner などが入っている前提
        result = {
            "winner": parsed.get("winner", "none"),
            "score_diff": parsed.get("score_diff", 0.0),
            "comment": parsed.get("comment", ""),
            "raw_text": raw_text,
            "parsed": parsed,
        }
        return result

    # ===== プロンプト構築 =====
    def _build_messages(self, models: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        各モデルの応答を A, B, C... として列挙し、
        どれが良いか JSON で答えてもらう。
        """

        # キーの順序は PARTICIPATING_MODELS をベースに整える
        ordered_keys: List[str] = []
        for k in PARTICIPATING_MODELS.keys():
            if k in models:
                ordered_keys.append(k)
        # 念のため、その他のキーも後ろに追加
        for k in models.keys():
            if k not in ordered_keys:
                ordered_keys.append(k)

        # A, B, C... に割り当て
        label_map: Dict[str, str] = {}
        rev_label_map: Dict[str, str] = {}
        label_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        for idx, key in enumerate(ordered_keys):
            if idx >= len(label_chars):
                break
            label = label_chars[idx]
            label_map[label] = key
            rev_label_map[key] = label

        lines: List[str] = []
        lines.append(
            "あなたは複数の AI 応答を比較し、物語としてより優れているものを選ぶ審判です。"
            "それぞれの応答は同じプロンプトに対する別モデルからの返答です。"
            "感情描写・文体の自然さ・キャラクター性・一貫性などを総合的に評価してください。"
        )
        lines.append("")
        lines.append("各応答にはラベル A, B, C... が割り当てられています。")
        lines.append("それぞれを読み比べ、もっとも良いと判断したラベルを 1 つ選んでください。")
        lines.append("")
        lines.append("=== 応答一覧 ===")

        for label, key in label_map.items():
            info = models.get(key, {})
            reply = str(info.get("reply") or "").strip()
            model_name = str(info.get("model_name") or key)
            lines.append(f"[{label}] model={model_name}")
            lines.append(reply)
            lines.append("")

        lines.append(
            "=== 出力フォーマット ===\n"
            "次の JSON だけを返してください（説明文やマークダウンは付けないでください）。\n"
            "{\n"
            '  "winner": "A" または "B" など、一番良いと判断したラベル,\n'
            '  "score_diff": 0.0 〜 1.0 程度のスコア差（自信の度合い）, \n'
            '  "comment": "日本語で、なぜそれを選んだかの短い説明"\n'
            "}\n"
            "同点で優劣がつけられない場合は winner を \"tie\" にしてください。"
        )

        system_prompt = (
            "あなたは物語文章の品質を評価する審判 AI です。"
            "指示された JSON 形式のみを返してください。"
        )

        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "\n".join(lines)},
        ]
        return messages

    # ===== モデル呼び出し =====
    def _call_judge(self, messages: List[Dict[str, str]]) -> Tuple[str, bool, Any]:
        try:
            resp = self.client.chat.completions.create(
                model=OPENAI_JUDGE_MODEL,
                messages=messages,
                temperature=0.3,
                max_tokens=800,
            )
        except BadRequestError as e:
            text = f"[Judge BadRequestError: {e}]"
            return text, False, None
        except Exception as e:  # noqa: BLE001
            text = f"[Judge Error: {e}]"
            return text, False, None

        text = resp.choices[0].message.content or ""

        # JSON パースを試みる
        parsed: Any
        ok = True
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            # ```json ... ``` で返ってくるケースへの簡易対応
            cleaned = text.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.strip("`")
                cleaned = cleaned.replace("json", "", 1).strip()
            try:
                parsed = json.loads(cleaned)
            except Exception:  # noqa: BLE001
                ok = False
                parsed = None

        return text, ok, parsed
