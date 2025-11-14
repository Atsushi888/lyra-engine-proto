# llm_router.py

import os
from typing import Any, Dict, List, Tuple

from openai import OpenAI, BadRequestError


# ====== 環境変数 ======
OPENAI_API_KEY_INITIAL = os.getenv("OPENAI_API_KEY")

# メイン側（GPT系）のモデル名（物語本体用）
MAIN_MODEL = os.getenv("OPENAI_MAIN_MODEL", "gpt-4o")

# ★ Judge / GPT-5.1 用
#   ・審判専用モデル（デフォルト：gpt-5.1）
#   ・「3人目の候補フローリア」も基本は同じモデルを使う
JUDGE_MODEL = os.getenv("OPENAI_JUDGE_MODEL", "gpt-5.1")
GPT5_CANDIDATE_MODEL = os.getenv("OPENAI_GPT5_CANDIDATE_MODEL", JUDGE_MODEL)

# ★ OpenRouter / Hermes 用
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_KEY_INITIAL = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
HERMES_MODEL = os.getenv("OPENROUTER_HERMES_MODEL", "nousresearch/hermes-4-70b")

if not OPENROUTER_API_KEY:
    raise ValueError("OPENROUTER_API_KEY is not set. Check Streamlit Secrets or environment.")


# ===== 共通 OpenAI 呼び出しヘルパ =====
def _call_openai_model(
    model: str,
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
) -> Tuple[str, Dict[str, Any]]:
    """
    任意の OpenAI Chat モデルを叩く共通ヘルパ。
    GPT-4o / GPT-5.1 / それ以外もここ経由。
    """
    api_key = os.getenv("OPENAI_API_KEY") or OPENAI_API_KEY_INITIAL
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY が設定されていません。")

    client = OpenAI(api_key=api_key)

    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=float(temperature),
        max_tokens=int(max_tokens),
    )

    text = resp.choices[0].message.content or ""

    usage: Dict[str, Any] = {}
    if getattr(resp, "usage", None) is not None:
        usage = {
            "prompt_tokens": getattr(resp.usage, "prompt_tokens", None),
            "completion_tokens": getattr(resp.usage, "completion_tokens", None),
            "total_tokens": getattr(resp.usage, "total_tokens", None),
        }

    return text, usage


# ====== GPT-4o（物語本体用） ======
def _call_gpt(
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
) -> Tuple[str, Dict[str, Any]]:
    """
    物語本体用の GPT 系メインモデル（デフォルト gpt-4o）。
    """
    return _call_openai_model(MAIN_MODEL, messages, temperature, max_tokens)


# ====== GPT-5.1（候補フローリア用） ======
def _call_gpt5_candidate(
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
) -> Tuple[str, Dict[str, Any]]:
    """
    マルチAI候補としての GPT-5.1。
    """
    return _call_openai_model(GPT5_CANDIDATE_MODEL, messages, temperature, max_tokens)


# ====== OpenRouter / Hermes ======
def _call_hermes(
    messages: List[Dict[str, str]],
    temperature: float,
    max_tokens: int,
) -> Tuple[str, Dict[str, Any]]:
    api_key = os.getenv("OPENROUTER_API_KEY") or OPENROUTER_API_KEY_INITIAL
    if not api_key:
        # キーが無いなら即ダミー返し
        return "[Hermes: OPENROUTER_API_KEY 未設定]", {
            "error": "OPENROUTER_API_KEY not set",
        }

    client_or = OpenAI(
        base_url=OPENROUTER_BASE_URL,
        api_key=OPENROUTER_API_KEY,
    )

    try:
        resp = client_or.chat.completions.create(
            model=HERMES_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    except BadRequestError as e:
        # 400 エラー（モデル非対応プロンプト等）はテキストとして返す
        return f"[Hermes BadRequestError: {e}]", {
            "error": str(e),
        }
    except Exception as e:
        return f"[Hermes Error: {e}]", {
            "error": str(e),
        }

    text = resp.choices[0].message.content or ""

    usage: Dict[str, Any] = {}
    if getattr(resp, "usage", None) is not None:
        usage = {
            "prompt_tokens": getattr(resp.usage, "prompt_tokens", None),
            "completion_tokens": getattr(resp.usage, "completion_tokens", None),
            "total_tokens": getattr(resp.usage, "total_tokens", None),
        }
    return text, usage


# ====== 公開インターフェース ======
def call_with_fallback(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 800,
) -> Tuple[str, Dict[str, Any]]:
    """
    物語本体用：GPT 系メイン（gpt-4o 等）を呼び出す。
    例外時は空文字とエラー meta を返す。
    """
    meta: Dict[str, Any] = {}
    try:
        text, usage = _call_gpt(messages, temperature, max_tokens)
        meta["route"] = "gpt"
        meta["model_main"] = MAIN_MODEL
        meta["usage_main"] = usage
        return text, meta
    except Exception as e:
        meta["route"] = "error"
        meta["gpt_error"] = str(e)
        return "", meta


def call_hermes(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 800,
) -> Tuple[str, Dict[str, Any]]:
    """
    Hermes 単体呼び出し。
    """
    text, usage = _call_hermes(messages, temperature, max_tokens)
    meta: Dict[str, Any] = {
        "route": "openrouter",
        "model_main": HERMES_MODEL,
        "usage_main": usage,
    }
    return text, meta


def call_gpt5_candidate(
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    max_tokens: int = 800,
) -> Tuple[str, Dict[str, Any]]:
    """
    マルチAI用の 3 人目候補として GPT-5.1 を呼ぶ。
    ※ 物語本体の返答にはまだ採用しない（Composer / Judge 用候補）
    """
    text, usage = _call_gpt5_candidate(messages, temperature, max_tokens)
    meta: Dict[str, Any] = {
        "route": "gpt5-candidate",
        "model_main": GPT5_CANDIDATE_MODEL,
        "usage_main": usage,
    }
    return text, meta


def call_judge_gpt5(
    messages: List[Dict[str, str]],
    temperature: float = 0.0,
    max_tokens: int = 800,
) -> Tuple[str, Dict[str, Any]]:
    """
    JudgeAI 専用：審判として GPT-5.1 を叩く。
    物語用とは完全に独立した呼び出し。
    """
    text, usage = _call_openai_model(JUDGE_MODEL, messages, temperature, max_tokens)
    meta: Dict[str, Any] = {
        "route": "judge-gpt5",
        "model_main": JUDGE_MODEL,
        "usage_main": usage,
    }
    return text, meta
