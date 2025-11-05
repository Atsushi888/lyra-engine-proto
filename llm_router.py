# llm_router.py — Lyra Engine unified LLM router
# GPT-5（OpenAI）を基本とし、失敗時のみ Hermes（OpenRouter）にフォールバックする

import os, json, requests, openai


# ======== APIキー設定 ========
openai.api_key = os.getenv("OPENAI_API_KEY")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE = "https://openrouter.ai/api/v1"


# ======== GPT-5 呼び出し ========
def _call_gpt5(messages, temperature=0.8, max_tokens=800):
    return openai.ChatCompletion.create(
        model="gpt-5-turbo",   # まだ開放されていない場合は "gpt-4o" に変更
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )


# ======== Hermes 呼び出し ========
def _call_hermes(messages, temperature=0.8, max_tokens=800):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "HTTP-Referer": "https://lyra-engine.example",
        "X-Title": "LyraEngine/HermesFallback",
    }
    payload = {
        "model": "nousresearch/hermes-3-llama-3-70b",
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    resp = requests.post(f"{OPENROUTER_BASE}/chat/completions",
                         headers=headers, json=payload, timeout=(10, 60))
    resp.raise_for_status()
    return resp.json()


# ======== レスポンス抽出 ========
def _extract_openai(resp):
    try:
        return resp["choices"][0]["message"]["content"].strip()
    except Exception:
        try:
            return resp.choices[0].message["content"].strip()
        except Exception:
            return ""


def _extract_openrouter(resp_json):
    try:
        return resp_json["choices"][0]["message"]["content"].strip()
    except Exception:
        return ""


# ======== GPT-5→Hermes フォールバック ========
def call_with_fallback(messages, temperature=0.8, max_tokens=800):
    """
    GPT-5（メイン） → Hermes（失敗時フォールバック）
    戻り値: (text, meta)
    """
    try:
        resp = _call_gpt5(messages, temperature=temperature, max_tokens=max_tokens)
        text = _extract_openai(resp)
        if not text or len(text) < 5:
            raise ValueError("Empty or too short response")
        return text, {"route": "gpt5"}
    except Exception as e:
        try:
            resp = _call_hermes(messages, temperature=temperature, max_tokens=max_tokens)
            text = _extract_openrouter(resp)
            if not text:
                raise ValueError("Hermes empty")
            return text, {"route": "hermes"}
        except Exception as e2:
            return "（返答の生成に失敗しました…）", {
                "route": "error",
                "gpt5_error": str(e),
                "hermes_error": str(e2),
            }
