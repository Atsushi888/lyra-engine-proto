# lyra_engine.py — Lyra Engine Prototype (Streamlit Edition, GPT-4o + Hermes fallback)
# 2025-11-07 build with PreflightChecker + DebugPanel + LyraEngine class

import os
import json
import html
import time
from typing import Any, Dict, List, Tuple

import streamlit as st

from personas import get_persona
from llm_router import call_with_fallback


# ================== ページ設定（最初に一度だけ） ==================
st.set_page_config(page_title="Lyra Engine – フローリア", layout="wide")
st.markdown(
    """
<style>
.block-container {
  max-width: 1100px;
  padding-left: 2rem;
  padding-right: 2rem;
}
.chat-bubble {
  white-space: pre-wrap;
  overflow-wrap:anywhere;
  word-break:break-word;
  line-height:1.7;
  padding:.8rem 1rem;
  border-radius:.7rem;
  margin:.35rem 0;
}
.chat-bubble.user {
  background:#f4f6fb;
}
.chat-bubble.assistant {
  background:#eaf7ff;
}
</style>
""",
    unsafe_allow_html=True,
)


# ================== Preflight / Debug 用クラス ==================
class PreflightChecker:
    """APIキーの有効性をざっくり確認するだけのクラス"""

    def __init__(self, openai_key: str | None, openrouter_key: str | None):
        self.openai_key = openai_key or ""
        self.openrouter_key = openrouter_key or ""

    def check_openai(self) -> bool:
        return bool(self.openai_key)

    def check_openrouter(self) -> bool:
        return bool(self.openrouter_key)

    def render(self) -> None:
        st.subheader("🧪 起動前診断 (Preflight)")
        ok_oa = self.check_openai()
        ok_or = self.check_openrouter()

        if ok_oa:
            st.success("✅ OPENAI: OpenAI API キーは有効です。")
        else:
            st.error("❌ OPENAI: OpenAI API キーが設定されていません。")

        if ok_or:
            st.success("✅ OPENROUTER: OpenRouter キー有効（Hermes 利用可）。")
        else:
            st.info("ℹ️ OPENROUTER: キー未設定のため Hermes は使用されません。")


class DebugPanel:
    """最後の LLM 呼び出しメタ情報を表示する小さなデバッグパネル"""

    def render(self, meta: Dict[str, Any] | None) -> None:
        show_dbg = st.checkbox("🧠 デバッグを表示", False)
        if not show_dbg:
            return

        st.markdown("###### 最後の LLM 呼び出し情報")
        if meta:
            st.json(meta)
        else:
            st.info("まだ LLM 呼び出し情報はありません。")


# ================== メインアプリクラス ==================
class LyraEngine:
    MAX_LOG = 500
    DISPLAY_LIMIT = 20000  # 表示上限（保存はフル）

    def __init__(self):
        # ペルソナ読み込み
        persona = get_persona("floria_ja")
        self.system_prompt: str = persona.system_prompt
        self.starter_hint: str = persona.starter_hint
        self.partner_name: str = persona.name

        # シークレット読み込み
        self.openai_key = st.secrets.get(
            "OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", "")
        )
        self.openrouter_key = st.secrets.get(
            "OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY", "")
        )

        if not self.openai_key:
            st.error(
                "OPENAI_API_KEY が未設定です。Streamlit → Settings → Secrets で設定してください。"
            )
            st.stop()

        # llm_router 側が os.getenv を参照するので、念のため流しておく
        os.environ["OPENAI_API_KEY"] = self.openai_key
        if self.openrouter_key:
            os.environ["OPENROUTER_API_KEY"] = self.openrouter_key

        # Preflight / Debug パネル
        self.preflight = PreflightChecker(self.openai_key, self.openrouter_key)
        self.debug_panel = DebugPanel()

        # session_state 初期化
        self._init_session_state()

    # ---------- session_state 管理 ----------
    @property
    def state(self):
        return st.session_state

    def _init_session_state(self) -> None:
        # 共通フラグ類
        defaults = {
            "user_input": "",
            "show_hint": False,
            "_busy": False,
            "_do_send": False,
            "_pending_text": "",
            "_clear_input": False,
            "_do_reset": False,
            "_ask_reset": False,
            "_last_call_meta": None,
            # 設定値（スライダーのデフォルト）
            "ui_temperature": 0.70,
            "ui_max_tokens": 800,
            "ui_wrap_width": 80,
        }
        for k, v in defaults.items():
            if k not in self.state:
                self.state[k] = v

        if "messages" not in self.state:
            self.state["messages"] = [
                {"role": "system", "content": self.system_prompt}
            ]

    def _handle_flags(self) -> None:
        """入力クリア・リセットなどのフラグを、UI描画前に処理する"""
        # 入力クリア
        if self.state.get("_clear_input"):
            self.state["_clear_input"] = False
            # ★ テキストエリア描画「前」にクリアするのが重要（ここでやる）
            self.state["user_input"] = ""

        # 会話リセット
        if self.state.get("_do_reset"):
            self.state["_do_reset"] = False
            self.state.update(
                {
                    "user_input": "",
                    "_pending_text": "",
                    "_busy": False,
                    "_do_send": False,
                    "_ask_reset": False,
                    "messages": [{"role": "system", "content": self.system_prompt}],
                    "_last_call_meta": None,
                }
            )

    # ---------- LLM 呼び出し ----------
    def call_llm(self, user_text: str) -> None:
        # ログ丸め
        if len(self.state["messages"]) > self.MAX_LOG:
            base_sys = self.state["messages"][0]
            self.state["messages"] = [base_sys] + self.state["messages"][
                -(self.MAX_LOG - 1) :
            ]

        # ユーザー発言追加
        self.state["messages"].append({"role": "user", "content": user_text})

        # コンテキスト（system + 直近 60件）
        base = self.state["messages"]
        max_slice = 60
        convo = [base[0]] + base[-max_slice:]

        temperature = float(self.state.get("ui_temperature", 0.70))
        max_tokens = int(self.state.get("ui_max_tokens", 800))

        with st.spinner(f"{self.partner_name}が考えています…"):
            reply, meta = call_with_fallback(
                convo,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        # デバッグ用メタ情報
        self.state["_last_call_meta"] = meta

        if not reply.strip():
            reply = "（返答の生成に失敗しました…）"

        self.state["messages"].append({"role": "assistant", "content": reply})

    # ---------- 各 UI セクション ----------
    def render_world_info(self) -> None:
        st.title("❄️ Lyra Engine — フローリア")

        with st.expander("世界観とあなたの役割（ロール）", expanded=False):
            st.markdown(
                """**舞台**：世界中を旅している旅人が、伴侶とした水と氷の精霊フローリアと、一夜を明かそうと身を寄せた場所。そこは、旅館か、街道筋か…。  
**あなた**：世界を巡る旅人。観察者ではなく、語りかけ・問いかけ・提案で物語を動かす当事者。  
**お願い**：命令口調よりも、状況描写や気持ち・意図を添えて話しかけると、会話が豊かになります。"""
            )
            st.checkbox("入力ヒントを表示する", key="show_hint")

    def render_settings(self) -> None:
        with st.expander("⚙️ 接続設定", expanded=False):
            c1, c2, c3 = st.columns(3)
            st.slider(
                "temperature",
                0.0,
                1.5,
                0.70,
                0.05,
                key="ui_temperature",
            )
            st.slider(
                "max_tokens（1レス上限）",
                64,
                4096,
                800,
                16,
                key="ui_max_tokens",
            )
            st.slider(
                "折り返し幅",
                20,
                100,
                80,
                1,
                key="ui_wrap_width",
            )

            # 折り返し幅に応じて CSS 反映
            wrap_width = int(self.state.get("ui_wrap_width", 80))
            st.markdown(
                f"<style>.chat-bubble {{ max-width: min(90vw, {wrap_width}ch); }}</style>",
                unsafe_allow_html=True,
            )

    def render_chat_log(self) -> None:
        st.subheader("💬 会話ログ")
        dialog = [
            m for m in self.state["messages"] if m["role"] in ("user", "assistant")
        ]

        for m in dialog:
            role = m["role"]
            raw = m["content"].strip()
            shown = (
                raw
                if len(raw) <= self.DISPLAY_LIMIT
                else (raw[: self.DISPLAY_LIMIT] + " …[truncated]")
            )
            txt = html.escape(shown)

            if role == "user":
                st.markdown(
                    f"<div class='chat-bubble user'><b>あなた：</b><br>{txt}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div class='chat-bubble assistant'><b>{self.partner_name}：</b><br>{txt}</div>",
                    unsafe_allow_html=True,
                )

    def render_debug_panel(self) -> None:
        meta = self.state.get("_last_call_meta")
        self.debug_panel.render(meta)

    def render_input(self) -> None:
        # ヒントボタン → テキストエリアを描画する「前」なら代入してOK
        hint_col, _ = st.columns([1, 3])
        if hint_col.button("ヒントを入力欄に挿入", disabled=self.state["_busy"]):
            self.state["user_input"] = self.starter_hint

        st.text_area(
            "あなたの言葉（複数行OK・空行不要）",
            key="user_input",
            height=160,
            placeholder=(self.starter_hint if self.state.get("show_hint") else ""),
        )

        # ボタン群
        c_send, c_new, c_show, c_dl = st.columns([1, 1, 1, 1])

        # 送信ボタン
        if c_send.button(
            "送信",
            type="primary",
            disabled=(self.state["_busy"] or self.state["_ask_reset"]),
        ):
            txt = self.state.get("user_input", "").strip()
            if txt:
                self.state["_pending_text"] = txt
                self.state["_do_send"] = True
                self.state["_clear_input"] = True
                st.rerun()

        # 新しい会話（確認付き）
        if self.state.get("_ask_reset", False):
            with st.container():
                st.warning("会話履歴がすべて消えます。続行しますか？")
                cc1, cc2 = st.columns(2)
                confirm = cc1.button("はい、リセットする", use_container_width=True)
                cancel = cc2.button("やめる", use_container_width=True)
                if confirm:
                    self.state["_do_reset"] = True
                    self.state["_ask_reset"] = False
                    st.rerun()
                elif cancel:
                    self.state["_ask_reset"] = False
        else:
            if c_new.button(
                "新しい会話（履歴が消えます）",
                use_container_width=True,
                disabled=(self.state["_busy"] or self.state["_ask_reset"]),
            ):
                self.state["_ask_reset"] = True
                st.rerun()

        # 最近10件
        if c_show.button(
            "最近10件を表示",
            use_container_width=True,
            disabled=(self.state["_busy"] or self.state["_ask_reset"]),
        ):
            st.info("最近10件の会話を下に表示します。")
            recent = [
                m
                for m in self.state["messages"]
                if m["role"] in ("user", "assistant")
            ][-10:]
            for m in recent:
                role = "あなた" if m["role"] == "user" else self.partner_name
                st.write(f"**{role}**：{m['content'].strip()}")

        # 保存・読込
        if c_dl.button(
            "JSON をダウンロード",
            use_container_width=True,
        ):
            st.download_button(
                "JSON をダウンロード",
                json.dumps(self.state["messages"], ensure_ascii=False, indent=2),
                file_name="floria_chat_log.json",
                mime="application/json",
                use_container_width=True,
            )

    def render_log_io(self) -> None:
        st.markdown("---")
        st.subheader("会話ログの読み込み")

        up = st.file_uploader("保存した JSON を選択", type=["json"])
        col_l, col_m, col_r = st.columns(3)
        load_mode = col_l.radio("読込モード", ["置き換え", "末尾に追記"], horizontal=True)
        show_preview = col_m.checkbox("内容をプレビュー", value=True)
        do_load = col_r.button(
            "読み込む",
            use_container_width=True,
            disabled=(
                up is None or self.state.get("_busy", False) or self.state["_ask_reset"]
            ),
        )

        if up is not None:
            try:
                imported = json.load(up)
                ok = isinstance(imported, list) and all(
                    isinstance(x, dict) and "role" in x and "content" in x
                    for x in imported
                )
                if not ok:
                    st.error(
                        "JSON 形式が不正です。messages の配列（各要素に role と content）が必要です。"
                    )
                else:
                    if show_preview:
                        st.caption("先頭5件プレビュー")
                        st.json(imported[:5])
                    if do_load:
                        if not (
                            len(imported) > 0
                            and imported[0].get("role") == "system"
                        ):
                            imported = [
                                {"role": "system", "content": self.system_prompt}
                            ] + imported

                        if load_mode == "置き換え":
                            self.state["messages"] = imported
                        else:
                            base = self.state.get(
                                "messages",
                                [{"role": "system", "content": self.system_prompt}],
                            )
                            tail = (
                                imported[1:]
                                if (
                                    len(imported) > 0
                                    and imported[0].get("role") == "system"
                                )
                                else imported
                            )
                            self.state["messages"] = base + tail

                        # フラグ類リセット
                        self.state.update(
                            {
                                "_pending_text": "",
                                "_do_send": False,
                                "_busy": False,
                                "_clear_input": False,
                                "_do_reset": False,
                            }
                        )
                        self.state["_last_call_meta"] = None
                        st.success("読込が完了しました。")
                        st.rerun()
            except Exception as e:
                st.error(f"JSON の読み込みに失敗しました：{e}")

    # ---------- メインループ ----------
    def run(self) -> None:
        # まずフラグ処理（ここで user_input をクリアするので安全）
        self._handle_flags()

        # 上部セクション
        self.preflight.render()
        self.render_world_info()
        self.render_settings()

        # 会話ログ & デバッグ
        self.render_chat_log()
        self.render_debug_panel()

        # 送信処理（LLM 呼び出し）
        if self.state["_do_send"] and not self.state["_busy"]:
            self.state["_do_send"] = False
            self.state["_busy"] = True
            try:
                txt = self.state.get("_pending_text", "")
                self.state["_pending_text"] = ""
                if txt:
                    self.call_llm(txt)
            finally:
                self.state["_busy"] = False
                st.rerun()

        # 入力欄 & ログ入出力
        self.render_input()
        self.render_log_io()


# ================== エントリポイント ==================
if __name__ == "__main__":
    app = LyraEngine()
    app.run()
