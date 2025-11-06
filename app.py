# app.py — Lyra Engine Prototype (Streamlit Edition, GPT-4o + Hermes fallback)

import os, json, html, time, streamlit as st
from persona_floria_ja import get_default_persona  # 現時点ではデフォルト人格として利用
from personas import get_persona
# from llm_router import call_with_fallback


# ================== 定数（人格から取得） ==================
# persona = get_default_persona()
persona = get_persona( "floria_ja" )
SYSTEM_PROMPT = persona.system_prompt
STARTER_HINT = persona.starter_hint
PARTNER_NAME = persona.name

MAX_LOG = 500
DISPLAY_LIMIT = 20000  # 20K文字の表示上限（保存はフル）

# ================== ページ設定 ==================
st.set_page_config(page_title="Lyra Engine Prototype", layout="wide")
st.markdown("""
<style>
.block-container { max-width: 1100px; padding-left: 2rem; padding-right: 2rem; }
.chat-bubble { white-space: pre-wrap; overflow-wrap:anywhere; word-break:break-word;
  line-height:1.7; padding:.8rem 1rem; border-radius:.7rem; margin:.35rem 0; }
.chat-bubble.user { background:#f4f6fb; }
.chat-bubble.assistant { background:#eaf7ff; }
</style>
""", unsafe_allow_html=True)

# ================== session_state 初期化 ==================
if "user_input" not in st.session_state:
    st.session_state["user_input"] = ""
if "show_hint" not in st.session_state:
    st.session_state["show_hint"] = False

DEFAULTS = {
    "_busy": False,
    "_do_send": False,
    "_pending_text": "",
    "_clear_input": False,
    "_do_reset": False,
    "_ask_reset": False,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# --- フラグ処理 ---
if st.session_state.get("_clear_input"):
    st.session_state["_clear_input"] = False
    st.session_state["user_input"] = ""

if st.session_state.get("_do_reset"):
    st.session_state["_do_reset"] = False
    st.session_state.update({
        "user_input": "",
        "_pending_text": "",
        "_busy": False,
        "_do_send": False,
        "_ask_reset": False,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}],
    })

# ================== 会話状態 ==================
if "messages" not in st.session_state:
    st.session_state["messages"] = [{"role": "system", "content": SYSTEM_PROMPT}]

# ================== シークレット ==================
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
OPENROUTER_API_KEY = st.secrets.get("OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY", ""))

if not OPENAI_API_KEY:
    st.error("OPENAI_API_KEY が未設定です。Streamlit → Settings → Secrets で設定してください。")
    st.stop()

# llm_router が os.getenv で読むので環境変数に流す
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
if OPENROUTER_API_KEY:
    os.environ["OPENROUTER_API_KEY"] = OPENROUTER_API_KEY

# ================== パラメータUI ==================
st.title("❄️ Lyra Engine Prototype")
with st.expander("世界観とあなたの役割（ロール）", expanded=False):
    # エンジンとしては中立の説明にする（具体的なキャラ名は persona 側の責務）
    st.markdown(
        """**概要**：この画面は「人格（ペルソナ）×対話エンジン」の挙動を確認するためのプロトタイプです。  
現在はデフォルトのペルソナと対話していますが、将来的には複数人格を切り替えて利用できます。  

**あなた**：物語世界の登場人物として、相手に語りかけ・問いかけ・提案を行う当事者です。  
**お願い**：命令口調よりも、状況描写や気持ち・意図を添えて話しかけると、対話が豊かになります。"""
    )
    st.checkbox("入力ヒントを表示する", key="show_hint")

with st.expander("接続設定", expanded=False):
    c1, c2, c3 = st.columns(3)
    temperature = c1.slider("temperature", 0.0, 1.5, 0.70, 0.05)
    max_tokens  = c2.slider("max_tokens（1レス上限）", 64, 4096, 800, 16)
    wrap_width  = c3.slider("折り返し幅", 20, 100, 80, 1)

    r1, r2 = st.columns(2)
    # いまはフォールバック先の LLM 内部で完結した1レス生成なので、「未使用」と明記
    auto_continue = r1.checkbox("長文を自動で継ぎ足す（未使用）", True)
    max_cont      = r2.slider("最大継ぎ足し回数（未使用）", 1, 6, 3)

st.markdown(
    f"<style>.chat-bubble {{ max-width: min(90vw, {wrap_width}ch); }}</style>",
    unsafe_allow_html=True
)

# ================== 接続テスト ==================
with st.expander("接続テスト（任意）", expanded=False):
    if st.button("モデルへテストリクエスト"):
        test_msgs = [
            {"role": "system", "content": "ping"},
            {"role": "user", "content": "pong?"},
        ]
        try:
            with st.spinner("テスト中…"):
                reply, meta = call_with_fallback(
                    test_msgs,
                    temperature=0.0,
                    max_tokens=16,
                )
            st.code(json.dumps(meta, ensure_ascii=False, indent=2), language="json")
            st.success(f"返信: {reply}")
        except Exception as e:
            st.error(f"接続エラー: {e}")

# ================== 送信関数（エンジン本体） ==================
def engine_say(user_text: str):
    """現在のペルソナと会話するためのコア関数。LLMの詳細は llm_router 側に隠蔽。"""
    # ログ丸め
    if len(st.session_state["messages"]) > MAX_LOG:
        base_sys = st.session_state["messages"][0]
        st.session_state["messages"] = [base_sys] + st.session_state["messages"][-(MAX_LOG - 1):]

    # ユーザー発言を履歴に追加
    st.session_state["messages"].append({"role": "user", "content": user_text})

    # 送るコンテキスト（system + 直近）
    base = st.session_state["messages"]
    max_slice = 60
    convo = [base[0]] + base[-max_slice:]

    with st.spinner(f"{PARTNER_NAME}が考えています…"):
        reply, meta = call_with_fallback(
            convo,
            temperature=float(temperature),
            max_tokens=int(max_tokens),
        )

    # デバッグ表示用
    st.session_state["_last_call_meta"] = meta

    if not reply.strip():
        reply = "（返答の生成に失敗しました…）"

    st.session_state["messages"].append({"role": "assistant", "content": reply})

# ================== 会話表示 ==================
st.subheader("会話")
dialog = [m for m in st.session_state["messages"] if m["role"] in ("user", "assistant")]

for m in dialog:
    role = m["role"]
    raw = m["content"].strip()
    shown = raw if len(raw) <= DISPLAY_LIMIT else (raw[:DISPLAY_LIMIT] + " …[truncated]")
    txt = html.escape(shown)
    if role == "user":
        st.markdown(
            f"<div class='chat-bubble user'><b>あなた：</b><br>{txt}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div class='chat-bubble assistant'><b>{PARTNER_NAME}：</b><br>{txt}</div>",
            unsafe_allow_html=True,
        )

# ================== デバッグ情報 ==================
show_dbg = st.checkbox("デバッグを表示", False)
if show_dbg and "_last_call_meta" in st.session_state:
    st.markdown("###### 最後の呼び出し情報")
    st.json(st.session_state["_last_call_meta"])

# ================== 入力欄 ==================
hint_col, _ = st.columns([1, 3])
if hint_col.button("ヒントを入力欄に挿入", disabled=st.session_state["_busy"]):
    st.session_state["user_input"] = STARTER_HINT

st.text_area(
    "あなたの言葉（複数行OK・空行不要）",
    key="user_input",
    height=160,
    placeholder=(STARTER_HINT if st.session_state.get("show_hint") else ""),
)

# ================== ボタン群 ==================
c_send, c_new, c_show, c_dl = st.columns([1, 1, 1, 1])

if c_send.button(
    "送信",
    type="primary",
    disabled=(st.session_state["_busy"] or st.session_state["_ask_reset"]),
):
    txt = st.session_state.get("user_input", "").strip()
    if txt:
        st.session_state["_pending_text"] = txt
        st.session_state["_do_send"] = True
        st.session_state["_clear_input"] = True
        st.rerun()

if st.session_state["_do_send"] and not st.session_state["_busy"]:
    st.session_state["_do_send"] = False
    st.session_state["_busy"] = True
    try:
        txt = st.session_state.get("_pending_text", "")
        st.session_state["_pending_text"] = ""
        if txt:
            engine_say(txt)
    finally:
        st.session_state["_busy"] = False
        st.rerun()

# ================== 新しい会話 ==================
if st.session_state.get("_ask_reset", False):
    with st.container():
        st.warning("会話履歴がすべて消えます。続行しますか？")
        cc1, cc2 = st.columns(2)
        confirm = cc1.button("はい、リセットする", use_container_width=True)
        cancel = cc2.button("やめる", use_container_width=True)
        if confirm:
            st.session_state["_do_reset"] = True
            st.session_state["_ask_reset"] = False
            st.rerun()
        elif cancel:
            st.session_state["_ask_reset"] = False
else:
    if c_new.button(
        "新しい会話（履歴が消えます）",
        use_container_width=True,
        disabled=(st.session_state["_busy"] or st.session_state["_ask_reset"]),
    ):
        st.session_state["_ask_reset"] = True
        st.rerun()

# ================== 最近10件 ==================
if c_show.button(
    "最近10件を表示",
    use_container_width=True,
    disabled=(st.session_state["_busy"] or st.session_state["_ask_reset"]),
):
    st.info("最近10件の会話を下に表示します。")
    recent = [m for m in st.session_state["messages"] if m["role"] in ("user", "assistant")][-10:]
    for m in recent:
        role_label = "あなた" if m["role"] == "user" else PARTNER_NAME
        st.write(f"**{role_label}**：{m['content'].strip()}")

# ================== 保存・読込 ==================
st.markdown("---")
st.subheader("会話ログの保存")
st.download_button(
    "JSON をダウンロード",
    json.dumps(st.session_state["messages"], ensure_ascii=False, indent=2),
    file_name="lyra_chat_log.json",
    mime="application/json",
    use_container_width=True,
)

st.subheader("会話ログの読み込み")
up = st.file_uploader("保存した JSON を選択", type=["json"])
col_l, col_m, col_r = st.columns(3)
load_mode = col_l.radio("読込モード", ["置き換え", "末尾に追記"], horizontal=True)
show_preview = col_m.checkbox("内容をプレビュー", value=True)
do_load = col_r.button(
    "読み込む",
    use_container_width=True,
    disabled=(up is None or st.session_state.get("_busy", False) or st.session_state["_ask_reset"]),
)

if up is not None:
    try:
        imported = json.load(up)
        ok = isinstance(imported, list) and all(
            isinstance(x, dict) and "role" in x and "content" in x for x in imported
        )
        if not ok:
            st.error("JSON 形式が不正です。messages の配列（各要素に role と content）が必要です。")
        else:
            if show_preview:
                st.caption("先頭5件プレビュー")
                st.json(imported[:5])
            if do_load:
                # system が先頭にないログには、現在の SYSTEM_PROMPT を補う
                if not (len(imported) > 0 and imported[0].get("role") == "system"):
                    imported = [{"role": "system", "content": SYSTEM_PROMPT}] + imported

                if load_mode == "置き換え":
                    st.session_state["messages"] = imported
                else:
                    base = st.session_state.get(
                        "messages",
                        [{"role": "system", "content": SYSTEM_PROMPT}],
                    )
                    tail = (
                        imported[1:]
                        if (len(imported) > 0 and imported[0].get("role") == "system")
                        else imported
                    )
                    st.session_state["messages"] = base + tail

                st.session_state.update({
                    "_pending_text": "",
                    "_do_send": False,
                    "_busy": False,
                    "_clear_input": False,
                    "_do_reset": False,
                })
                st.session_state.pop("_last_call_meta", None)

                st.success("読込が完了しました。")
                st.rerun()
    except Exception as e:
        st.error(f"JSON の読み込みに失敗しました：{e}")
